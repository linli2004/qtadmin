from sqlalchemy.orm import Session
from human.models.talent import Talent, TalentStatus

def get_pipeline(db: Session) -> dict:
    talents = db.query(Talent).filter(Talent.status != TalentStatus.CLOSED).all()
    stages = {s.value: [] for s in TalentStatus}
    for t in talents:
        stages[t.status.value].append(_talent_to_card(t))
    summary = {"total": len(talents), "by_stage": {}}
    for s in TalentStatus:
        count = len(stages[s.value])
        if count > 0:
            summary["by_stage"][s.value] = count
    return {"stages": stages, "summary": summary}

def _talent_to_card(t: Talent) -> dict:
    return {
        "id": t.id, "email": t.email, "real_name": t.real_name,
        "recruitment_id": t.recruitment_id, "status": t.status.value,
        "sub_stage": t.sub_stage, "quality": t.quality,
        "stage_results": t.stage_results,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
