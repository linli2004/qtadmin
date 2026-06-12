from sqlalchemy.orm import Session
from human.models.talent import TalentStatus
from human.models.application import Application

def get_headcount(db: Session, recruitment_id: int) -> dict:
    total = db.query(Application).filter(
        Application.recruitment_id == recruitment_id,
        Application.status == TalentStatus.OFFER,
        Application.pooled_at.is_(None),
    ).count()
    accepted = db.query(Application).filter(
        Application.recruitment_id == recruitment_id,
        Application.status == TalentStatus.OFFER,
        Application.sub_stage == "accepted",
    ).count()
    return {"recruitment_id": recruitment_id, "total_offers": total, "accepted": accepted}
