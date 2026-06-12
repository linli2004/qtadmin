from datetime import datetime
from sqlalchemy import DateTime, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from human.database import Base

class PendingQueueItem(Base):
    __tablename__ = "pending_queue"
    __table_args__ = (UniqueConstraint("message_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(500))
    sender_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sender_email: Mapped[str | None] = mapped_column(String(200), nullable=False)
    suggested_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[str] = mapped_column(String(10), default="low")
    hr_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
