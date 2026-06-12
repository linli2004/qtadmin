from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.schemas.export import TrainingPairResponse
from app.human.services.export import count_training_pairs, get_training_pairs

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/training-pairs", response_model=TrainingPairResponse)
def list_training_pairs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    items = get_training_pairs(db, skip=skip, limit=limit)
    total = count_training_pairs(db)
    return TrainingPairResponse(items=items, total=total)
