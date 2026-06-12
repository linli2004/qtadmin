from datetime import datetime
from pydantic import BaseModel

class ConfirmRequest(BaseModel):
    action: str = "confirmed"; status: str = "contacted"
    real_name: str = ""; email: str = ""

class ConfirmResponse(BaseModel):
    queue_id: int; action: str; talent_id: int | None = None

class IgnoreRequest(BaseModel):
    action: str = "ignored"

class QueueItemRead(BaseModel):
    queue_id: int; message_id: str; subject: str
    sender_name: str | None; sender_email: str | None
    suggested_status: str | None; confidence: str
    hr_status: str; created_at: str

class IngestItem(BaseModel):
    message_id: str; subject: str
    sender_name: str = ""; sender_email: str = ""
    suggested_status: str = "contacted"; confidence: str = "low"

class IngestRequest(BaseModel):
    source: str = "example"; items: list[IngestItem]

class IngestResponse(BaseModel):
    batch_id: str | None; queued: int; skipped: int; errors: list[str]
