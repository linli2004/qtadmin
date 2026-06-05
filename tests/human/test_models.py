"""Tests for HR domain models and enums."""
import pytest
from sqlalchemy import text

from app.human.models.talent import ALLOWED_STATUSES_FOR_SUB_STAGE, STATUS_TRANSITIONS, Talent, TalentStatus
from app.human.models.recruitment import Recruitment
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.models.pending_queue import PendingQueueItem


class TestTalentStatus:
    def test_all_values(self):
        assert [s.value for s in TalentStatus] == [
            "new", "contacted", "exam_sent", "exam_received",
            "evaluating", "interview", "offer", "closed",
        ]

    def test_str_values(self):
        assert TalentStatus.NEW.value == "new"
        assert TalentStatus.CONTACTED.value == "contacted"

    def test_all_keys_in_transitions(self):
        for s in TalentStatus:
            assert s in STATUS_TRANSITIONS, f"{s} missing from STATUS_TRANSITIONS"


class TestStatusTransitions:
    def test_new_can_contacted(self):
        assert TalentStatus.CONTACTED in STATUS_TRANSITIONS[TalentStatus.NEW]

    def test_new_can_close(self):
        assert TalentStatus.CLOSED in STATUS_TRANSITIONS[TalentStatus.NEW]

    def test_new_cannot_exam_sent(self):
        assert TalentStatus.EXAM_SENT not in STATUS_TRANSITIONS[TalentStatus.NEW]

    def test_contacted_can_exam_sent(self):
        assert TalentStatus.EXAM_SENT in STATUS_TRANSITIONS[TalentStatus.CONTACTED]

    def test_contacted_can_close(self):
        assert TalentStatus.CLOSED in STATUS_TRANSITIONS[TalentStatus.CONTACTED]

    def test_evaluating_can_return_exam_sent(self):
        assert TalentStatus.EXAM_SENT in STATUS_TRANSITIONS[TalentStatus.EVALUATING]

    def test_evaluating_can_interview(self):
        assert TalentStatus.INTERVIEW in STATUS_TRANSITIONS[TalentStatus.EVALUATING]

    def test_offer_only_closed(self):
        assert STATUS_TRANSITIONS[TalentStatus.OFFER] == [TalentStatus.CLOSED]

    def test_closed_no_transitions(self):
        assert STATUS_TRANSITIONS[TalentStatus.CLOSED] == []

    def test_invalid_transition_new_to_offer(self):
        assert TalentStatus.OFFER not in STATUS_TRANSITIONS[TalentStatus.NEW]


class TestAllowedSubStages:
    def test_contacted_allowed(self):
        assert TalentStatus.CONTACTED in ALLOWED_STATUSES_FOR_SUB_STAGE

    def test_new_not_allowed(self):
        assert TalentStatus.NEW not in ALLOWED_STATUSES_FOR_SUB_STAGE

    def test_closed_not_allowed(self):
        assert TalentStatus.CLOSED not in ALLOWED_STATUSES_FOR_SUB_STAGE


class TestRecruitmentModel:
    def test_create_and_read(self, db):
        r = Recruitment()
        db.add(r)
        db.commit()
        assert r.id is not None
        assert r.created_at is not None

    def test_list(self, db):
        for _ in range(3):
            db.add(Recruitment())
        db.commit()
        rows = db.query(Recruitment).all()
        assert len(rows) == 3


class TestTalentModel:
    def test_create_minimal(self, db):
        r = Recruitment()
        db.add(r)
        db.flush()
        t = Talent(recruitment_id=r.id, email="a@b.com", real_name="测试")
        db.add(t)
        db.commit()
        assert t.id is not None
        assert t.status == TalentStatus.NEW

    def test_default_quality(self, db):
        r = Recruitment()
        db.add(r)
        db.flush()
        t = Talent(recruitment_id=r.id, email="a@b.com", real_name="测试")
        db.add(t)
        db.commit()
        assert t.quality == "normal"

    def test_sub_stage(self, db):
        r = Recruitment()
        db.add(r)
        db.flush()
        t = Talent(recruitment_id=r.id, email="a@b.com", real_name="测试")
        t.sub_stage = "resume_passed"
        db.add(t)
        db.commit()
        assert t.sub_stage == "resume_passed"


class TestCandidateModel:
    def test_create(self, db):
        c = Candidate(email="c@d.com", real_name="候选人")
        db.add(c)
        db.commit()
        assert c.id is not None
        assert c.phone is None

    def test_email_unique_not_enforced_by_model(self, db):
        """Model itself doesn't enforce email uniqueness; that's app-level."""
        db.add(Candidate(email="dup@test.com", real_name="A"))
        db.add(Candidate(email="dup@test.com", real_name="B"))
        db.commit()
        assert db.query(Candidate).count() == 2


class TestApplicationModel:
    def test_create(self, db):
        r = Recruitment()
        db.add(r)
        db.flush()
        c = Candidate(email="a@b.com", real_name="测试")
        db.add(c)
        db.flush()
        a = Application(candidate_id=c.id, recruitment_id=r.id)
        db.add(a)
        db.commit()
        assert a.id is not None
        assert a.status == TalentStatus.NEW
        assert a.source == "manual"

    def test_candidate_relationship(self, db):
        r = Recruitment()
        db.add(r)
        db.flush()
        c = Candidate(email="rel@test.com", real_name="关系测试")
        db.add(c)
        db.flush()
        a = Application(candidate_id=c.id, recruitment_id=r.id)
        db.add(a)
        db.commit()
        db.refresh(a)
        assert a.candidate.email == "rel@test.com"
        assert a.candidate.real_name == "关系测试"


class TestPendingQueueItemModel:
    def test_create(self, db):
        qi = PendingQueueItem(
            message_id="msg_001",
            subject="求职简历",
            sender_name="张三",
            sender_email="zhangsan@test.com",
            suggested_status="contacted",
            confidence="high",
        )
        db.add(qi)
        db.commit()
        assert qi.id is not None
        assert qi.hr_status == "pending"

    def test_unique_message_id(self, db):
        db.add(PendingQueueItem(message_id="unique_1", subject="S1", sender_email="a@b.com"))
        db.commit()
        db.add(PendingQueueItem(message_id="unique_1", subject="S2", sender_email="a@b.com"))
        with pytest.raises(Exception):
            db.commit()

    def test_default_confidence(self, db):
        qi = PendingQueueItem(message_id="msg_dc", subject="S1", sender_email="a@b.com")
        db.add(qi)
        db.commit()
        assert qi.confidence == "low"
