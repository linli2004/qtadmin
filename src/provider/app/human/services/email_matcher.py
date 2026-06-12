from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.human.models.application import Application
from app.human.models.candidate import Candidate


@dataclass
class MatchResult:
    exists: bool
    candidate_id: int | None = None
    candidate_name: str | None = None
    active_application_id: int | None = None
    merge_result: str = "new"  # "new" | "existing_auto" | "existing_review"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _subject_matches_recruitment(subject: str, recruitment_title: str) -> bool:
    if not recruitment_title:
        return False
    keywords = recruitment_title.lower().split()
    subject_lower = subject.lower()
    return any(kw in subject_lower for kw in keywords)


def match_by_email(email: str, db: Session, subject: str = "") -> MatchResult:
    if not email:
        return MatchResult(exists=False)

    normalized = _normalize_email(email)

    candidates = (
        db.query(Candidate)
        .filter(func.lower(Candidate.email) == normalized)
        .order_by(Candidate.created_at.desc())
        .all()
    )

    if not candidates:
        return MatchResult(exists=False)

    # Multiple Candidates with same email → ambiguous, escalate
    if len(candidates) > 1:
        return MatchResult(
            exists=True,
            merge_result="existing_review",
        )

    candidate = candidates[0]
    active_apps = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate.id,
            Application.deactivated_at.is_(None),
        )
        .order_by(Application.created_at.desc())
        .all()
    )

    if not active_apps:
        return MatchResult(
            exists=True,
            candidate_id=candidate.id,
            candidate_name=candidate.real_name,
            merge_result="existing_review",
        )

    # Single active application
    if len(active_apps) == 1:
        return MatchResult(
            exists=True,
            candidate_id=candidate.id,
            candidate_name=candidate.real_name,
            active_application_id=active_apps[0].id,
            merge_result="existing_auto",
        )

    # Multiple active applications: try to disambiguate by subject
    for app in active_apps:
        recruitment_title = app.recruitment.title if hasattr(app, "recruitment") and app.recruitment else ""
        if recruitment_title and _subject_matches_recruitment(subject, recruitment_title):
            return MatchResult(
                exists=True,
                candidate_id=candidate.id,
                candidate_name=candidate.real_name,
                active_application_id=app.id,
                merge_result="existing_auto",
            )

    return MatchResult(
        exists=True,
        candidate_id=candidate.id,
        candidate_name=candidate.real_name,
        merge_result="existing_review",
    )
