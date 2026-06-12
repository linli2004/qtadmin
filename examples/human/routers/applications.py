from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from human.database import get_db
from human.models.application import Application
from human.schemas.application import ApplicationRead

router = APIRouter(prefix="/applications", tags=["human"])

@router.get("", response_model=list[ApplicationRead])
def list_applications(status: str | None = None, pooled: bool | None = None,
                      skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
                      db: Session = Depends(get_db)):
    qb = db.query(Application)
    if status: qb = qb.filter(Application.status == status)
    if pooled is True: qb = qb.filter(Application.pooled_at.isnot(None))
    elif pooled is False: qb = qb.filter(Application.pooled_at.is_(None))
    return qb.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()
