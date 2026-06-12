"""HR Demo — Standalone server with Feishu integration.

整合了 quanttide-hr-toolkit-main 的完整 demo 架构：
  - 招聘管道 API（所有 routers）
  - 飞书邮箱轮询（`_poll_mailbox` 后台任务）
  - 附件下载（lark-cli + httpx）
  - 种子数据 + 数据库迁移
  - 静态前端

Usage:
    cd qtadmin
    QTADMIN_MAILBOX=xxx@example.com PYTHONPATH=src/provider src/provider/.venv/bin/python examples/human/demo.py
"""
import asyncio
import json
import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.human.database import SessionLocal, init_db
from app.human.models.processed_mail import ProcessedMail
from app.human.models.recruitment import Recruitment
from app.human.routers import (
    ai_config, applications, candidates, export, ingest, materials, messages,
    pipeline, pool, queue, recruitments,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.environ.get("QTADMIN_DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
_ATTACHMENT_DIR = os.path.join(_DATA_DIR, "attachments")
_MATERIALS_DIR = os.path.join(_DATA_DIR, "materials")


def seed_data_if_empty():
    db = SessionLocal()
    try:
        exists = db.query(Recruitment).first()
        if not exists:
            from app.human.seed import seed_data
            seed_data(db)
    finally:
        db.close()


def _download_attachment(message_id: str, attachment: dict, mailbox: str) -> str | None:
    """Download attachment via lark-cli download_url, return local path."""
    att_id = attachment.get("message_attachment_id")
    if not att_id:
        return None

    cmd = [
        "lark-cli", "mail", "user_mailbox.message.attachments", "download_url",
        "--params", json.dumps({
            "user_mailbox_id": mailbox or "me",
            "message_id": message_id,
            "attachment_ids": [att_id],
        }),
        "--format", "json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        result.check_returncode()
        resp = json.loads(result.stdout)
        urls = resp.get("data", {}).get("download_urls", [])
        if not urls:
            return None
        download_url = urls[0].get("download_url", "")
        if not download_url:
            return None
    except Exception:
        return None

    storage_dir = os.path.join(_ATTACHMENT_DIR, message_id)
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, attachment["filename"])

    try:
        r = httpx.get(download_url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
        attachment["size"] = len(r.content)
        return file_path
    except Exception:
        return None


def _fetch_mail(mailbox: str) -> list[dict]:
    from feishu_integration.mail_reader import fetch_and_classify, fetch_single_email
    items = fetch_and_classify(mailbox=mailbox)
    for item in items:
        try:
            detail = fetch_single_email(item["message_id"], mailbox=mailbox)
            item["body"] = detail.get("body", "")
            item["body_text"] = detail.get("body_plain_text", "")
            item["recipient_email"] = detail.get("to", "")
            attachments = []
            for a in detail.get("attachments", []):
                att = {
                    "filename": a.get("filename", ""),
                    "size": a.get("size", 0),
                    "mime_type": a.get("content_type", ""),
                    "message_attachment_id": a.get("message_attachment_id") or a.get("id", ""),
                }
                if att["mime_type"] in ("application/pdf",) or att["filename"].endswith(".pdf"):
                    storage_path = _download_attachment(item["message_id"], att, mailbox)
                    if storage_path:
                        att["storage_path"] = storage_path
                attachments.append(att)
            item["attachments"] = attachments
        except Exception:
            pass
    return items


async def _poll_mailbox():
    mailbox = os.environ.get("QTADMIN_MAILBOX", "")
    if not mailbox:
        return
    while True:
        try:
            items = await asyncio.to_thread(_fetch_mail, mailbox)
            db = SessionLocal()
            try:
                known = {row[0] for row in db.query(ProcessedMail.message_id).all()}
                new_items = [it for it in items if it["message_id"] not in known]
                for item in new_items:
                    db.add(ProcessedMail(message_id=item["message_id"]))
                db.commit()
            finally:
                db.close()
            if new_items:
                payload = {
                    "source": "feishu_api",
                    "items": [
                        {
                            "message_id": item["message_id"],
                            "subject": item["subject"],
                            "sender_name": item.get("sender_name", ""),
                            "sender_email": item["sender_email"],
                            "recipient_email": item.get("recipient_email", ""),
                            "suggested_status": item.get("suggested_status"),
                            "confidence": item.get("confidence", "low"),
                            "body": item.get("body"),
                            "body_text": item.get("body_text"),
                            "attachments": item.get("attachments"),
                        }
                        for item in new_items
                    ],
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "http://localhost:8000/ingest",
                        json=payload,
                        timeout=30,
                    )
                    resp.raise_for_status()
        except Exception:
            pass
        await asyncio.sleep(300)


_poll_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in [_ATTACHMENT_DIR, _MATERIALS_DIR]:
        os.makedirs(d, exist_ok=True)
    init_db()
    seed_data_if_empty()
    global _poll_task
    _poll_task = asyncio.create_task(_poll_mailbox())
    yield
    if _poll_task:
        _poll_task.cancel()


app = FastAPI(title="HR Demo — 招聘管道看板", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    if request.url.path in ("/",) or request.url.path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080", "http://localhost:8080",
        "http://127.0.0.1:8081", "http://localhost:8081",
        "http://127.0.0.1:8000", "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_config.router)
app.include_router(export.router)
app.include_router(materials.router)
app.include_router(messages.router)
app.include_router(ingest.router)
app.include_router(queue.router)
app.include_router(pipeline.router)
app.include_router(pool.router)
app.include_router(recruitments.router)
app.include_router(candidates.router)
app.include_router(applications.router)


@app.get("/attachments/{message_id}/{filename:path}")
def serve_attachment(message_id: str, filename: str):
    """Serve stored attachment files for browser preview."""
    file_path = os.path.join(_ATTACHMENT_DIR, message_id, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(file_path, filename=filename)


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
