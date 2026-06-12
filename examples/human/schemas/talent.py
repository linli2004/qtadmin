from datetime import datetime
from pydantic import BaseModel, Field
from human.models.talent import TalentStatus

class TalentCreate(BaseModel):
    email: str
    real_name: str
    auto_screening_result: str | None = None

class TalentRead(BaseModel):
    id: int; recruitment_id: int; email: str; real_name: str
    status: TalentStatus; sub_stage: str | None; quality: str
    stage_results: dict | None; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}

class TalentUpdate(BaseModel):
    email: str | None = None; real_name: str | None = None
    model_config = {"extra": "forbid"}

class TalentTransition(BaseModel):
    status: TalentStatus; sub_stage: str | None = None

class SubStageUpdate(BaseModel):
    sub_stage: str | None = None
