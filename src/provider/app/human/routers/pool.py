from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.human.database import get_db
from app.human.models.application import Application
from app.human.schemas.application import PoolItemRead
from app.human.services.pool import get_pooled_applications

router = APIRouter(prefix="/pool", tags=["human"])


def _pool_item_from_orm(app: Application) -> dict:
    return {
        "id": app.id,
        "candidate_id": app.candidate_id,
        "recruitment_id": app.recruitment_id,
        "status": app.status,
        "sub_stage": app.sub_stage,
        "quality": app.quality,
        "stage_results": app.stage_results,
        "source": app.source,
        "pooled_at": app.pooled_at,
        "deactivated_at": app.deactivated_at,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "candidate_email": app.candidate.email,
        "candidate_name": app.candidate.real_name,
    }


@router.get("", response_model=list[PoolItemRead])
def list_pooled_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    apps = get_pooled_applications(db, skip=skip, limit=limit)
    return [_pool_item_from_orm(a) for a in apps]
