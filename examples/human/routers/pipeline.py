from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from human.database import get_db
from human.services.pipeline import get_pipeline

router = APIRouter(tags=["human"])

@router.get("/pipeline")
def pipeline_view(db: Session = Depends(get_db)):
    return get_pipeline(db)
