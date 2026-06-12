from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from human.database import get_db
from human.models.application import Application
from human.services.pool import get_pooled_applications, pool_application, unpool_application
from human.schemas.application import PoolItemRead, UnpoolRequest

router = APIRouter(prefix="/pool", tags=["human"])

def _pool_item_from_orm(app: Application) -> dict:
    return {
        "id": app.id, "candidate_id": app.candidate_id, "recruitment_id": app.recruitment_id,
        "status": app.status.value, "source": app.source,
        "pooled_at": app.pooled_at.isoformat() if app.pooled_at else None,
        "deactivated_at": app.deactivated_at.isoformat() if app.deactivated_at else None,
        "candidate_email": app.candidate.email if app.candidate else "",
        "candidate_name": app.candidate.real_name if app.candidate else "",
    }

@router.get("", response_model=list[dict])
def list_pool(db: Session = Depends(get_db)):
    apps = get_pooled_applications(db)
    return [_pool_item_from_orm(a) for a in apps]

@router.post("/{application_id}/pool", response_model=dict)
def pool_app(application_id: int, db: Session = Depends(get_db)):
    try:
        app = pool_application(db, application_id)
        return _pool_item_from_orm(app)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.post("/{application_id}/unpool", status_code=201, response_model=dict)
def unpool_app(application_id: int, data: UnpoolRequest, db: Session = Depends(get_db)):
    try:
        app = unpool_application(db, application_id, data.recruitment_id)
        return _pool_item_from_orm(app)
    except ValueError as e:
        raise HTTPException(400, str(e))
