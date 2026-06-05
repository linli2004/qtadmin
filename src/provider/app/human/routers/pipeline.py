from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.services.pipeline import get_pipeline

router = APIRouter(prefix="/pipeline", tags=["human"])


@router.get("")
def pipeline(db: Session = Depends(get_db)):
    return get_pipeline(db)
