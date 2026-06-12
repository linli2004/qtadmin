from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from human.models.application import Application
from human.models.talent import TalentStatus

def pool_application(db: Session, application_id: int) -> Application:
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError("Application not found")
    now = datetime.now(timezone.utc)
    app.pooled_at = now
    app.deactivated_at = now
    app.status = TalentStatus.CLOSED
    db.commit()
    db.refresh(app)
    return app

def unpool_application(db: Session, application_id: int, recruitment_id: int) -> Application:
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError("Application not found")
    if app.pooled_at is None:
        raise ValueError("Application is not pooled")
    new_app = Application(
        candidate_id=app.candidate_id, recruitment_id=recruitment_id,
        status=TalentStatus.NEW, source="pool",
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app

def get_pooled_applications(db: Session) -> list[Application]:
    return (db.query(Application)
            .options(joinedload(Application.candidate))
            .filter(Application.pooled_at.isnot(None))
            .order_by(Application.pooled_at.desc()).all())
