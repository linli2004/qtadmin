from datetime import datetime
from pydantic import BaseModel, Field
from human.models.talent import TalentStatus

class ApplicationRead(BaseModel):
    id: int; candidate_id: int; recruitment_id: int
    status: TalentStatus; sub_stage: str | None; quality: str
    stage_results: dict | None; source: str
    pooled_at: datetime | None; deactivated_at: datetime | None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}

class PoolItemRead(BaseModel):
    id: int; candidate_id: int; recruitment_id: int
    status: TalentStatus; source: str
    pooled_at: datetime | None; deactivated_at: datetime | None
    candidate_email: str = ""; candidate_name: str = ""
    model_config = {"from_attributes": True}

class UnpoolRequest(BaseModel):
    recruitment_id: int = Field(..., ge=1)
