"""Processed mail tracking for Feishu mailbox polling dedup."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.human.database import Base


class ProcessedMail(Base):
    __tablename__ = "processed_mails"
    message_id: str = Column(String(255), primary_key=True)
    processed_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
