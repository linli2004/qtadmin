"""Queue management — HR confirm, ignore, and stats."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.pending_queue import PendingQueueItem
from app.human.models.recruitment import Recruitment
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.models.talent import Talent, TalentStatus

router = APIRouter(prefix="/queue", tags=["human"])


class ConfirmRequest(BaseModel):
    action: str = "confirmed"
    status: str = "contacted"
    real_name: str = ""
    email: str = ""
    recruitment_title: str | None = None


class ConfirmResponse(BaseModel):
    queue_id: int
    action: str
    talent_id: int | None = None


class IgnoreRequest(BaseModel):
    action: str = "ignored"


class QueueItemRead(BaseModel):
    queue_id: int
    message_id: str
    subject: str
    sender_name: str | None = None
    sender_email: str = ""
    suggested_status: str | None = None
    confidence: str = "low"
    hr_status: str = "pending"
    created_at: str = ""

    model_config = {"from_attributes": True}


class QueueListResponse(BaseModel):
    items: list[QueueItemRead]
    total: int


@router.get("", response_model=QueueListResponse)
def list_queue(
    hr_status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    qb = db.query(PendingQueueItem)
    if hr_status:
        qb = qb.filter(PendingQueueItem.hr_status == hr_status)
    total = qb.count()
    items = qb.order_by(PendingQueueItem.created_at.desc()).offset(skip).limit(limit).all()

    return QueueListResponse(
        items=[QueueItemRead(
            queue_id=item.id,
            message_id=item.message_id,
            subject=item.subject,
            sender_name=item.sender_name,
            sender_email=item.sender_email,
            suggested_status=item.suggested_status,
            confidence=item.confidence,
            hr_status=item.hr_status,
            created_at=str(item.created_at),
        ) for item in items],
        total=total,
    )


@router.patch("/{queue_id}/confirm", response_model=ConfirmResponse)
def confirm_queue_item(queue_id: int, body: ConfirmRequest, db: Session = Depends(get_db)):
    item = db.query(PendingQueueItem).filter(PendingQueueItem.id == queue_id).first()
    if not item:
        raise HTTPException(404, "Queue item not found")

    item.hr_status = body.action
    db.flush()

    recruitment = db.query(Recruitment).order_by(Recruitment.created_at.desc()).first()
    if not recruitment:
        recruitment = Recruitment()
        db.add(recruitment)
        db.flush()

    candidate = db.query(Candidate).filter(Candidate.email == (body.email or item.sender_email)).first()
    if not candidate:
        candidate = Candidate(
            email=body.email or item.sender_email,
            real_name=body.real_name or item.sender_name or "未知",
        )
        db.add(candidate)
        db.flush()

    app = Application(
        candidate_id=candidate.id,
        recruitment_id=recruitment.id,
        source="feishu_api",
    )
    db.add(app)
    db.flush()

    target_status = body.status or item.suggested_status
    if target_status and target_status != "new":
        try:
            status_order = ["new", "contacted", "exam_sent", "exam_received", "evaluating", "interview", "offer", "closed"]
            from app.human.models.talent import STATUS_TRANSITIONS
            current_idx = status_order.index(app.status.value)
            target_idx = status_order.index(target_status)
            for s in status_order[current_idx + 1 : target_idx + 1]:
                if TalentStatus(s) in STATUS_TRANSITIONS.get(app.status, []):
                    app.status = TalentStatus(s)
                    db.flush()
        except (ValueError, KeyError):
            pass

    talent = Talent(
        recruitment_id=recruitment.id,
        email=candidate.email,
        real_name=candidate.real_name,
        status=app.status,
    )
    db.add(talent)
    db.commit()
    db.refresh(talent)

    return ConfirmResponse(queue_id=item.id, action=body.action, talent_id=talent.id)


@router.patch("/{queue_id}/ignore", response_model=ConfirmResponse)
def ignore_queue_item(queue_id: int, body: IgnoreRequest, db: Session = Depends(get_db)):
    item = db.query(PendingQueueItem).filter(PendingQueueItem.id == queue_id).first()
    if not item:
        raise HTTPException(404, "Queue item not found")
    item.hr_status = "ignored"
    db.commit()
    return ConfirmResponse(queue_id=item.id, action="ignored")


@router.get("/stats")
def queue_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT hr_status, COUNT(*) as cnt FROM pending_queue GROUP BY hr_status")
    ).all()
    return {row[0]: row[1] for row in rows} or {"pending": 0, "confirmed": 0, "ignored": 0}
