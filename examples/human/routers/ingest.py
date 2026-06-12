from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from human.database import get_db
from human.models.pending_queue import PendingQueueItem
from human.schemas.pending_queue import IngestRequest, IngestResponse

router = APIRouter(tags=["human"])

@router.post("/ingest", status_code=201, response_model=IngestResponse)
def ingest_items(data: IngestRequest, db: Session = Depends(get_db)):
    queued = 0; skipped = 0; errors = []
    for item in data.items:
        exists = db.query(PendingQueueItem).filter(PendingQueueItem.message_id == item.message_id).first()
        if exists:
            skipped += 1; continue
        qi = PendingQueueItem(message_id=item.message_id, subject=item.subject,
                             sender_name=item.sender_name, sender_email=item.sender_email,
                             suggested_status=item.suggested_status, confidence=item.confidence)
        db.add(qi); queued += 1
    db.commit()
    return IngestResponse(batch_id=None, queued=queued, skipped=skipped, errors=errors)
