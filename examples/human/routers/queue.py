from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from human.database import get_db
from human.models.pending_queue import PendingQueueItem
from human.models.recruitment import Recruitment
from human.models.talent import Talent, TalentStatus
from human.models.candidate import Candidate
from human.models.application import Application
from human.schemas.pending_queue import ConfirmRequest, ConfirmResponse, IgnoreRequest

router = APIRouter(prefix="/queue", tags=["human"])

@router.get("")
def list_queue(hr_status: str | None = None, db: Session = Depends(get_db)):
    qb = db.query(PendingQueueItem).order_by(PendingQueueItem.created_at.desc())
    if hr_status:
        qb = qb.filter(PendingQueueItem.hr_status == hr_status)
    items = qb.all()
    return {"total": len(items), "items": [{
        "queue_id": qi.id, "message_id": qi.message_id,
        "subject": qi.subject, "sender_name": qi.sender_name,
        "sender_email": qi.sender_email, "suggested_status": qi.suggested_status,
        "confidence": qi.confidence, "hr_status": qi.hr_status,
        "created_at": str(qi.created_at),
    } for qi in items]}

@router.patch("/{queue_id}/confirm", response_model=ConfirmResponse)
def confirm_queue_item(queue_id: int, data: ConfirmRequest, db: Session = Depends(get_db)):
    qi = db.query(PendingQueueItem).filter(PendingQueueItem.id == queue_id).first()
    if not qi:
        raise HTTPException(404, "Queue item not found")
    qi.hr_status = "confirmed"; db.flush()
    recruitment = db.query(Recruitment).order_by(Recruitment.created_at.desc()).first()
    if not recruitment:
        recruitment = Recruitment(); db.add(recruitment); db.flush()
    email = data.email or qi.sender_email or "unknown@email.com"
    name = data.real_name or qi.sender_name or email.split("@")[0]
    status = TalentStatus(data.status) if data.status else TalentStatus.CONTACTED
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    if not candidate:
        candidate = Candidate(email=email, real_name=name); db.add(candidate); db.flush()
    app = Application(candidate_id=candidate.id, recruitment_id=recruitment.id, status=status, source="email_queue")
    db.add(app); db.flush()
    talent = Talent(recruitment_id=recruitment.id, email=email, real_name=name, status=status)
    db.add(talent); db.commit(); db.refresh(talent)
    return ConfirmResponse(queue_id=queue_id, action="confirmed", talent_id=talent.id)

@router.patch("/{queue_id}/ignore", response_model=ConfirmResponse)
def ignore_queue_item(queue_id: int, data: IgnoreRequest = None, db: Session = Depends(get_db)):
    qi = db.query(PendingQueueItem).filter(PendingQueueItem.id == queue_id).first()
    if not qi:
        raise HTTPException(404, "Queue item not found")
    qi.hr_status = "ignored"; db.commit()
    return ConfirmResponse(queue_id=queue_id, action="ignored")

@router.get("/stats")
def queue_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    counts = db.query(PendingQueueItem.hr_status, func.count(PendingQueueItem.id)).group_by(PendingQueueItem.hr_status).all()
    stats = {"pending": 0, "confirmed": 0, "ignored": 0}
    for status, count in counts:
        if status in stats: stats[status] = count
    return stats

@router.get("/by-email")
def get_queue_by_email(email: str, db: Session = Depends(get_db)):
    qi = db.query(PendingQueueItem).filter(PendingQueueItem.sender_email == email).order_by(PendingQueueItem.created_at.desc()).first()
    if not qi:
        return {"found": False}
    return {"found": True, "item": {"queue_id": qi.id, "message_id": qi.message_id, "subject": qi.subject,
                                     "sender_name": qi.sender_name, "sender_email": qi.sender_email,
                                     "suggested_status": qi.suggested_status, "confidence": qi.confidence,
                                     "hr_status": qi.hr_status}}
