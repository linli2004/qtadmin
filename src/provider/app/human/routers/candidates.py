from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.schemas.candidate import CandidateRead
from app.human.schemas.application import ApplicationRead

router = APIRouter(prefix="/candidates", tags=["human"])


@router.get("", response_model=list[CandidateRead])
def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return db.query(Candidate).order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{candidate_id}/applications", response_model=list[ApplicationRead])
def get_candidate_applications(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(404, "Candidate not found")
    return db.query(Application).filter(Application.candidate_id == candidate_id).all()
