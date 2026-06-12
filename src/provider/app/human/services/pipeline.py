"""Pipeline aggregation service."""
from sqlalchemy.orm import Session

from app.human.models.talent import Talent, TalentStatus


def get_pipeline(db: Session) -> dict:
    stages = {}
    total = 0
    for status in TalentStatus:
        talents = (
            db.query(Talent)
            .filter(Talent.status == status)
            .order_by(Talent.updated_at.desc())
            .all()
        )
        stages[status.value] = [_talent_to_card(t) for t in talents]
        total += len(talents)

    need_attention = len(stages.get("exam_received", [])) + len(stages.get("evaluating", []))
    return {
        "stages": stages,
        "summary": {
            "total": total,
            "by_stage": {s.value: len(stages.get(s.value, [])) for s in TalentStatus},
            "need_attention": need_attention,
        },
    }


def _talent_to_card(t: Talent) -> dict:
    return {
        "id": t.id,
        "email": t.email,
        "real_name": t.real_name,
        "recruitment_id": t.recruitment_id,
        "status": t.status.value,
        "sub_stage": t.sub_stage,
        "quality": t.quality,
        "stage_results": t.stage_results,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
    }
