from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.application import Application
from app.human.models.talent import TalentStatus
from app.human.schemas.application import ApplicationRead, UnpoolRequest
from app.human.services.pool import pool_application, unpool_application

router = APIRouter(prefix="/applications", tags=["human"])


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    status: TalentStatus | None = None,
    candidate_id: int | None = Query(default=None, ge=1),
    recruitment_id: int | None = Query(default=None, ge=1),
    pooled: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    qb = db.query(Application)
    if status:
        qb = qb.filter(Application.status == status)
    if candidate_id:
        qb = qb.filter(Application.candidate_id == candidate_id)
    if recruitment_id:
        qb = qb.filter(Application.recruitment_id == recruitment_id)
    if pooled is True:
        qb = qb.filter(Application.pooled_at.isnot(None))
    elif pooled is False:
        qb = qb.filter(Application.pooled_at.is_(None))
    return qb.order_by(Application.updated_at.desc()).offset(skip).limit(limit).all()


@router.post("/{application_id}/pool", response_model=ApplicationRead)
def pool_application_endpoint(application_id: int, db: Session = Depends(get_db)):
    app = pool_application(db, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.post("/{application_id}/unpool", response_model=ApplicationRead, status_code=201)
def unpool_application_endpoint(application_id: int, body: UnpoolRequest, db: Session = Depends(get_db)):
    original = db.query(Application).filter(Application.id == application_id).first()
    if not original:
        raise HTTPException(404, "Application not found")
    if original.pooled_at is None:
        raise HTTPException(400, "Application is not pooled")
    new_app = unpool_application(db, application_id, body.recruitment_id)
    return new_app
