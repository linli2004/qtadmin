"""HR models."""
from app.human.models.talent import Talent, TalentStatus
from app.human.models.recruitment import Recruitment
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.models.pending_queue import PendingQueueItem
from app.human.models.processed_mail import ProcessedMail

__all__ = [
    "Talent", "TalentStatus",
    "Recruitment",
    "Candidate",
    "Application",
    "PendingQueueItem",
    "ProcessedMail",
]
