"""Human CLI commands — recruitment email classification and ingestion."""
import json
import sys

import httpx
import typer

from app.human.api_client import ApiClient
from app.human.classifier import classify
from app.human.config import Config
from app.human.lark_client import LarkClient

app = typer.Typer(help="人力资源职能：招聘邮件处理")
config_app = typer.Typer(help="查看和修改人力资源模块配置")


@config_app.command(name="set-provider")
def config_set_provider(url: str = typer.Argument(..., help="服务端地址，如 http://127.0.0.1:8000")):
    """配置服务端地址。"""
    Config().set("provider_url", url)
    typer.echo(f"服务端地址已设为: {url}")


@config_app.command(name="set-lark-path")
def config_set_lark_path(path: str = typer.Argument(..., help="lark-cli 路径")):
    """配置 lark-cli 路径。"""
    Config().set("lark_path", path)
    typer.echo(f"lark-cli 路径已设为: {path}")


@config_app.command(name="show")
def config_show():
    """查看当前配置。"""
    cfg = Config().show()
    for k, v in cfg.items():
        typer.echo(f"  {k} = {v}")


app.add_typer(config_app, name="config")


@app.command(name="list")
def mail_list(
    limit: int = typer.Option(20, "-n", "--limit", help="最大条数"),
    since: str = typer.Option("7d", "--since", help="时间范围（7d/24h/日期）"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """列出收件箱中的招聘邮件。"""
    cfg = Config()
    lark = LarkClient(lark_path=cfg.get("lark_path"))
    emails = lark.list_emails(limit=limit, since=since)

    if not emails:
        typer.echo("未找到招聘邮件。请确认 lark-cli 已安装并登录。", err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(
            [{"mail_id": e.mail_id, "subject": e.subject, "sender": e.sender_name, "date": e.date}
             for e in emails], ensure_ascii=False,
        ))
        return

    typer.echo(f" {'#':>3} │ {'发件人':<8} │ {'主题':<40} │ {'建议阶段':<14} │ {'可信度':<6}")
    typer.echo("─────┼──────────┼──────────────────────────────────────────┼────────────────┼────────")
    for i, email in enumerate(emails, 1):
        status, conf = classify(subject=email.subject, sender_email="")
        status_str = status or "待确认"
        typer.echo(f" {i:>3} │ {email.sender_name:<8} │ {email.subject:<40} │ {status_str:<14} │ {conf:<6}")


@app.command(name="classify")
def mail_classify(
    mail_id: str = typer.Argument(..., help="邮件 ID"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """对单封邮件运行分类并预览。"""
    cfg = Config()
    lark = LarkClient(lark_path=cfg.get("lark_path"))
    email = lark.read_email(mail_id)
    if not email:
        typer.echo(f"邮件 {mail_id} 未找到。用 list 命令查看可用 ID。", err=True)
        raise typer.Exit(1)

    status, conf = classify(subject=email.subject, body=email.body, sender_email=email.sender_email)

    if as_json:
        typer.echo(json.dumps({
            "mail_id": mail_id, "subject": email.subject,
            "sender_name": email.sender_name, "sender_email": email.sender_email,
            "suggested_status": status, "confidence": conf,
        }, ensure_ascii=False))
        return

    typer.echo(f"  发件人: {email.sender_name} <{email.sender_email}>")
    typer.echo(f"  主题:   {email.subject}")
    typer.echo(f"  建议:   {status or '无法分类'} (可信度: {conf})")


@app.command(name="ingest")
def mail_ingest(
    limit: int = typer.Option(20, "-n", "--limit", help="最多处理条数"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只预览，不推送"),
    status_filter: str = typer.Option(None, "--status", help="只推送指定阶段的邮件"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """推送分类结果到服务端待确认队列。"""
    cfg = Config()
    provider_url = cfg.get("provider_url")
    if not provider_url:
        typer.echo("未配置服务端地址。运行: qtadmin human config set-provider <url>", err=True)
        raise typer.Exit(1)

    lark = LarkClient(lark_path=cfg.get("lark_path"))
    emails = lark.list_emails(limit=limit)

    items = []
    for email in emails:
        status, conf = classify(subject=email.subject, sender_email=email.sender_email)
        if not status:
            continue
        if status_filter and status != status_filter:
            continue
        items.append({
            "message_id": email.mail_id, "subject": email.subject,
            "sender_name": email.sender_name, "sender_email": email.sender_email or "",
            "suggested_status": status, "confidence": conf,
        })

    if dry_run or not items:
        if as_json:
            typer.echo(json.dumps({"dry_run": True, "count": len(items), "items": items}, ensure_ascii=False))
            return
        typer.echo(f"\n  {'发件人':<8} │ {'主题':<30} │ {'建议阶段':<14} │ {'可信度':<6}")
        typer.echo("  ─────────┼─────────────────────────────────┼────────────────┼────────")
        for item in items:
            typer.echo(f"  {item['sender_name']:<8} │ {item['subject']:<30} │ {item['suggested_status']:<14} │ {item['confidence']:<6}")
        if dry_run:
            typer.echo(f"\n  预览: {len(items)} 条。去掉 --dry-run 执行推送。", err=True)
        else:
            typer.echo("没有可推送的邮件。", err=True)
        return

    try:
        api = ApiClient(base_url=provider_url)
        result = api.ingest(source="feishu_api", items=items)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        typer.echo(f"连接服务端失败: {e}", err=True)
        typer.echo(f"确认服务端已启动且 provider_url 配置正确。", err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(result, ensure_ascii=False))
        return

    typer.echo(f"  已入队列: {result['queued']}  已跳过: {result['skipped']}", err=True)
    if result["errors"]:
        typer.echo(f"  错误: {len(result['errors'])}", err=True)
    typer.echo(f"  数据已在待确认队列，请通过管理后台确认。", err=True)


@app.command()
def status(
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """查看待确认队列计数。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    try:
        stats = api.get_queue_stats()
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        typer.echo(f"连接服务端失败: {e}", err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(stats, ensure_ascii=False))
        return

    typer.echo(f"  待确认: {stats.get('pending', 0)}", err=True)
    typer.echo(f"  已确认: {stats.get('confirmed', 0)}", err=True)
    typer.echo(f"  已忽略: {stats.get('ignored', 0)}", err=True)
