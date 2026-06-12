from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from human.database import Base
from human.models.talent import TalentStatus

class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    recruitment_id: Mapped[int] = mapped_column(ForeignKey("recruitments.id"), index=True)
    candidate: Mapped["Candidate"] = relationship("Candidate", lazy="joined")
    status: Mapped[TalentStatus] = mapped_column(Enum(TalentStatus), default=TalentStatus.NEW, index=True)
    sub_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    quality: Mapped[str] = mapped_column(String(10), default="normal")
    stage_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    pooled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
