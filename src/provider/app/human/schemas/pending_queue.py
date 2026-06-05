"""Shared pending queue schemas."""

from pydantic import BaseModel


class ConfirmRequest(BaseModel):
    action: str = "confirmed"
    status: str = "contacted"
    real_name: str = ""
    email: str = ""
    recruitment_title: str | None = None


class ConfirmResponse(BaseModel):
    queue_id: int
    action: str
    talent_id: int | None = None


class IgnoreRequest(BaseModel):
    action: str = "ignored"
