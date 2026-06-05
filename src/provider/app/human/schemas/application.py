from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.human.models.talent import TalentStatus


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    recruitment_id: int
    status: TalentStatus
    sub_stage: str | None = None
    quality: str = "normal"
    stage_results: dict | None = None
    source: str = "manual_seed"
    pooled_at: datetime | None = None
    deactivated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UnpoolRequest(BaseModel):
    recruitment_id: int = Field(..., ge=1)


class PoolItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    recruitment_id: int
    status: TalentStatus
    sub_stage: str | None = None
    quality: str = "normal"
    stage_results: dict | None = None
    source: str = "manual_seed"
    pooled_at: datetime | None = None
    deactivated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    candidate_email: str = ""
    candidate_name: str = ""
