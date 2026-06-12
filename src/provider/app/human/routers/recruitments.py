from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.talent import ALLOWED_STATUSES_FOR_SUB_STAGE, STATUS_TRANSITIONS, Talent, TalentStatus
from app.human.models.recruitment import Recruitment
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.schemas.talent import SubStageUpdate, TalentCreate, TalentRead, TalentTransition, TalentUpdate
from app.human.schemas.recruitment import HeadcountRead, RecruitmentRead
from app.human.services.headcount import get_headcount

router = APIRouter(prefix="/recruitments", tags=["human"])


@router.get("", response_model=list[RecruitmentRead])
def list_recruitments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return db.query(Recruitment).order_by(Recruitment.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{recruitment_id}", response_model=RecruitmentRead)
def get_recruitment(recruitment_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruitment).filter(Recruitment.id == recruitment_id).first()
    if not r:
        raise HTTPException(404, "Recruitment not found")
    return r


@router.post("", response_model=RecruitmentRead, status_code=201)
def create_recruitment(db: Session = Depends(get_db)):
    r = Recruitment()
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{recruitment_id}", status_code=204)
def delete_recruitment(recruitment_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruitment).filter(Recruitment.id == recruitment_id).first()
    if not r:
        raise HTTPException(404, "Recruitment not found")
    db.delete(r)
    db.commit()


@router.get("/{recruitment_id}/headcount", response_model=HeadcountRead)
def get_recruitment_headcount(recruitment_id: int, db: Session = Depends(get_db)):
    _recruitment_exists(recruitment_id, db)
    return get_headcount(db, recruitment_id)


def _recruitment_exists(recruitment_id: int, db: Session) -> None:
    if not db.query(Recruitment).filter(Recruitment.id == recruitment_id).first():
        raise HTTPException(404, "Recruitment not found")


@router.get("/{recruitment_id}/talents", response_model=list[TalentRead])
def list_talents(
    recruitment_id: int,
    status: TalentStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _recruitment_exists(recruitment_id, db)
    qb = db.query(Talent).filter(Talent.recruitment_id == recruitment_id)
    if status:
        qb = qb.filter(Talent.status == status)
    return qb.order_by(Talent.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/{recruitment_id}/talents/{talent_id}", response_model=TalentRead)
def get_talent(recruitment_id: int, talent_id: int, db: Session = Depends(get_db)):
    t = db.query(Talent).filter(Talent.id == talent_id, Talent.recruitment_id == recruitment_id).first()
    if not t:
        raise HTTPException(404, "Talent not found")
    return t


@router.post("/{recruitment_id}/talents", response_model=TalentRead, status_code=201)
def create_talent(recruitment_id: int, data: TalentCreate, db: Session = Depends(get_db)):
    recruitment = db.query(Recruitment).filter(Recruitment.id == recruitment_id).first()
    if not recruitment:
        raise HTTPException(404, "Recruitment not found")

    candidate = db.query(Candidate).filter(Candidate.email == data.email.lower()).first()
    if not candidate:
        candidate = Candidate(email=data.email.lower(), real_name=data.real_name)
        db.add(candidate)
        db.flush()
    app = Application(candidate_id=candidate.id, recruitment_id=recruitment_id, source="manual_debug")
    db.add(app)
    db.flush()

    t = Talent(recruitment_id=recruitment_id, email=data.email, real_name=data.real_name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{recruitment_id}/talents/{talent_id}", response_model=TalentRead)
def update_talent(recruitment_id: int, talent_id: int, data: TalentUpdate, db: Session = Depends(get_db)):
    t = db.query(Talent).filter(Talent.id == talent_id, Talent.recruitment_id == recruitment_id).first()
    if not t:
        raise HTTPException(404, "Talent not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.post("/{recruitment_id}/talents/{talent_id}/transition", response_model=TalentRead)
def transition_talent(recruitment_id: int, talent_id: int, data: TalentTransition, db: Session = Depends(get_db)):
    t = db.query(Talent).filter(Talent.id == talent_id, Talent.recruitment_id == recruitment_id).first()
    if not t:
        raise HTTPException(404, "Talent not found")

    target = data.status
    if target not in STATUS_TRANSITIONS.get(t.status, []):
        raise HTTPException(400, f"Cannot transition from {t.status.value} to {target.value}")

    old_status = t.status

    candidate = db.query(Candidate).filter(Candidate.email == t.email).first()
    if candidate:
        app = (db.query(Application)
               .filter(Application.candidate_id == candidate.id,
                       Application.recruitment_id == recruitment_id)
               .order_by(Application.created_at.desc())
               .first())
        if app:
            app.status = target
            if target != old_status:
                app.sub_stage = None
            if data.sub_stage is not None and target in ALLOWED_STATUSES_FOR_SUB_STAGE:
                app.sub_stage = data.sub_stage

            stage_key = old_status.value
            if stage_key in ("contacted", "evaluating", "interview", "offer"):
                if not (stage_key == "evaluating" and target.value == "exam_sent"):
                    if app.stage_results is None:
                        app.stage_results = {}
                    app.stage_results[stage_key] = "pass" if target.value != "closed" else "fail"

            t.status = app.status
            t.sub_stage = app.sub_stage
            t.stage_results = app.stage_results

    db.commit()
    db.refresh(t)
    return t


@router.patch("/{recruitment_id}/talents/{talent_id}/sub-stage", response_model=TalentRead)
def set_talent_sub_stage(recruitment_id: int, talent_id: int, data: SubStageUpdate, db: Session = Depends(get_db)):
    t = db.query(Talent).filter(Talent.id == talent_id, Talent.recruitment_id == recruitment_id).first()
    if not t:
        raise HTTPException(404, "Talent not found")
    if t.status not in ALLOWED_STATUSES_FOR_SUB_STAGE:
        raise HTTPException(400, f"Cannot set sub_stage for status {t.status.value}")
    t.sub_stage = data.sub_stage
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{recruitment_id}/talents/{talent_id}", status_code=204)
def delete_talent(recruitment_id: int, talent_id: int, db: Session = Depends(get_db)):
    t = db.query(Talent).filter(Talent.id == talent_id, Talent.recruitment_id == recruitment_id).first()
    if not t:
        raise HTTPException(404, "Talent not found")
    db.delete(t)
    db.commit()
