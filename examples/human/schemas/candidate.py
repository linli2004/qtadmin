from datetime import datetime
from pydantic import BaseModel

class CandidateRead(BaseModel):
    id: int; email: str; real_name: str; phone: str | None; created_at: datetime
    model_config = {"from_attributes": True}
