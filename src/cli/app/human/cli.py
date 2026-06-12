"""Human CLI commands — recruitment email classification and ingestion."""
import json
import logging
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
        status, conf = classify(subject=email.subject, sender_email=email.sender_email)
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


@app.command(name="send")
def mail_send(
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """领取并发送发件箱中的待发邮件（单次轮询）。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    try:
        from app.human.mail_sender import send_pending
        sent = send_pending(api)
    except httpx.ConnectError as e:
        typer.echo(f"连接服务端失败: {e}", err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps({"sent": sent}, ensure_ascii=False))
        return

    if sent:
        typer.echo(f"已发送 {sent} 封邮件。", err=True)
    else:
        typer.echo("发件箱中没有待发邮件。", err=True)


@app.command(name="send-loop")
def mail_send_loop(
    interval: int = typer.Option(30, "-i", "--interval", help="轮询间隔（秒）"),
):
    """持续轮询发件箱并发送邮件（守护进程模式）。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    try:
        from app.human.mail_sender import run_loop
        run_loop(api, interval=interval)
    except KeyboardInterrupt:
        typer.echo("\n发件循环已停止。", err=True)


@app.command(name="outbox")
def mail_outbox(
    status: str = typer.Option(None, "--status", help="筛选状态: pending/sending/sent/failed"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """查看发件箱统计。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    count = api.get_outbox_count(status=status)
    if as_json:
        typer.echo(json.dumps({"count": count, "status": status}, ensure_ascii=False))
        return
    label = status or "待发/发送中"
    typer.echo(f"  {label}: {count} 封", err=True)


@app.command(name="dead-letters")
def mail_dead_letters(
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
):
    """查看死信队列（发送失败超过最大重试次数）。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    items = api.list_dead_letters()
    if as_json:
        typer.echo(json.dumps(items, ensure_ascii=False))
        return

    if not items:
        typer.echo("  没有死信。", err=True)
        return

    typer.echo(f"  {'#':>3} │ {'收件人':<24} │ {'主题':<40} │ {'失败原因':<20} │ {'重试次数'}")
    typer.echo("  ─────┼──────────────────────────┼──────────────────────────────────────────┼──────────────────────┼────────────")
    for i, item in enumerate(items, 1):
        typer.echo(f"  {i:>3} │ {item['recipient_email'] or '':<24} │ {item['subject'][:38]:<40} │ {(item['failure_reason'] or '')[:18]:<20} │ {item['retry_count']}")


@app.command(name="requeue")
def mail_requeue(
    message_id: int = typer.Argument(..., help="死信消息 ID"),
):
    """将死信重新放入发件队列。"""
    cfg = Config()
    api = ApiClient(base_url=cfg.get("provider_url"))
    try:
        result = api.requeue_dead_letter(message_id)
        typer.echo(f"  消息 {result['id']} 已重新入队，状态: {result['send_status']}", err=True)
    except httpx.HTTPStatusError as e:
        typer.echo(f"  操作失败 (HTTP {e.response.status_code}): {e.response.text}", err=True)
        raise typer.Exit(1)
