"""Ingest endpoint — receive raw emails from CLI, classify server-side, queue for HR review."""
import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.pending_queue import PendingQueueItem
from app.human.services.classifier import classify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["human"])


class IngestAttachment(BaseModel):
    filename: str
    size: int


class IngestItem(BaseModel):
    message_id: str
    subject: str
    sender_name: str | None = None
    sender_email: str
    suggested_status: str | None = None
    confidence: str = "low"
    suggested_recruitment_title: str | None = None
    body: str | None = None
    body_text: str | None = None
    attachments: list[IngestAttachment] | None = None


class IngestRequest(BaseModel):
    source: str = "feishu_api"
    batch_id: str | None = None
    items: list[IngestItem]


class IngestItemResult(BaseModel):
    message_id: str
    queue_id: int | None = None
    action: str


class IngestResponse(BaseModel):
    batch_id: str | None = None
    queued: int = 0
    skipped: int = 0
    errors: list[str] = []
    items: list[IngestItemResult]


@router.post("", response_model=IngestResponse, status_code=201)
def ingest_items(body: IngestRequest, db: Session = Depends(get_db)):
    existing = {
        row[0]
        for row in db.query(PendingQueueItem.message_id)
        .filter(PendingQueueItem.message_id.in_([i.message_id for i in body.items]))
        .all()
    }

    queued = 0
    skipped = 0
    results: list[IngestItemResult] = []
    errors: list[str] = []

    for item in body.items:
        if item.message_id in existing:
            results.append(IngestItemResult(message_id=item.message_id, action="skipped"))
            skipped += 1
            continue

        attachments_json = None
        if item.attachments:
            attachments_json = json.dumps([a.model_dump() for a in item.attachments], ensure_ascii=False)

        # Run server-side classification
        classification = classify(
            subject=item.subject,
            body_text=item.body_text,
            sender_name=item.sender_name,
            sender_email=item.sender_email,
            db=db,
        )

        qi = PendingQueueItem(
            source=body.source,
            message_id=item.message_id,
            subject=item.subject,
            sender_name=item.sender_name,
            sender_email=item.sender_email,
            body=item.body,
            body_text=item.body_text,
            suggested_status=classification.suggested_status,
            confidence=classification.confidence,
            suggested_recruitment_title=item.suggested_recruitment_title,
            attachments_json=attachments_json,
        )
        db.add(qi)
        db.flush()
        results.append(IngestItemResult(message_id=item.message_id, queue_id=qi.id, action="queued"))
        queued += 1

    db.commit()
    return IngestResponse(
        batch_id=body.batch_id,
        queued=queued,
        skipped=skipped,
        errors=errors,
        items=results,
    )
