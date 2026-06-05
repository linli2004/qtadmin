"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.human.models.talent import TalentStatus
from app.human.schemas.talent import (
    TalentCreate, TalentRead, TalentTransition, TalentUpdate, SubStageUpdate,
)
from app.human.schemas.recruitment import RecruitmentRead, HeadcountRead
from app.human.schemas.candidate import CandidateRead
from app.human.schemas.application import ApplicationRead, PoolItemRead, UnpoolRequest
from app.human.schemas.pending_queue import ConfirmRequest, ConfirmResponse, IgnoreRequest


class TestTalentCreate:
    def test_valid(self):
        s = TalentCreate(email="a@b.com", real_name="测试")
        assert s.email == "a@b.com"
        assert s.real_name == "测试"
        assert s.auto_screening_result is None

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            TalentCreate(real_name="测试")

    def test_missing_real_name(self):
        with pytest.raises(ValidationError):
            TalentCreate(email="a@b.com")


class TestTalentUpdate:
    def test_valid_partial(self):
        s = TalentUpdate(email="new@b.com")
        assert s.email == "new@b.com"
        assert s.real_name is None

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            TalentUpdate(invalid_field="x")

    def test_empty(self):
        s = TalentUpdate()
        assert s.model_dump(exclude_unset=True) == {}


class TestTalentTransition:
    def test_valid(self):
        s = TalentTransition(status=TalentStatus.CONTACTED)
        assert s.status == TalentStatus.CONTACTED

    def test_with_sub_stage(self):
        s = TalentTransition(status=TalentStatus.CONTACTED, sub_stage="resume_passed")
        assert s.sub_stage == "resume_passed"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            TalentTransition(status="invalid_status")


class TestSubStageUpdate:
    def test_none(self):
        s = SubStageUpdate()
        assert s.sub_stage is None

    def test_with_value(self):
        s = SubStageUpdate(sub_stage="interview_passed")
        assert s.sub_stage == "interview_passed"


class TestTalentRead:
    def test_from_attributes(self, db):
        from app.human.models.recruitment import Recruitment
        from app.human.models.talent import Talent

        r = Recruitment()
        db.add(r)
        db.flush()
        t = Talent(recruitment_id=r.id, email="a@b.com", real_name="测试")
        db.add(t)
        db.commit()

        schema = TalentRead.model_validate(t)
        assert schema.id == t.id
        assert schema.email == "a@b.com"
        assert schema.real_name == "测试"
        assert schema.status == TalentStatus.NEW
        assert schema.quality == "normal"


class TestRecruitmentRead:
    def test_from_attributes(self, db):
        from app.human.models.recruitment import Recruitment

        r = Recruitment()
        db.add(r)
        db.commit()

        schema = RecruitmentRead.model_validate(r)
        assert schema.id == r.id


class TestHeadcountRead:
    def test_create(self):
        s = HeadcountRead(recruitment_id=1, total_offers=5, accepted=3)
        assert s.total_offers == 5
        assert s.accepted == 3


class TestCandidateRead:
    def test_from_attributes(self, db):
        from app.human.models.candidate import Candidate

        c = Candidate(email="c@d.com", real_name="候选人")
        db.add(c)
        db.commit()

        schema = CandidateRead.model_validate(c)
        assert schema.email == "c@d.com"
        assert schema.real_name == "候选人"
        assert schema.phone is None


class TestApplicationRead:
    def test_from_attributes(self, db):
        from app.human.models.recruitment import Recruitment
        from app.human.models.candidate import Candidate
        from app.human.models.application import Application

        r = Recruitment()
        db.add(r)
        db.flush()
        c = Candidate(email="a@b.com", real_name="测试")
        db.add(c)
        db.flush()
        a = Application(candidate_id=c.id, recruitment_id=r.id)
        db.add(a)
        db.commit()

        schema = ApplicationRead.model_validate(a)
        assert schema.id == a.id
        assert schema.source == "manual"


class TestPoolItemRead:
    def test_from_attributes(self, db):
        from app.human.models.recruitment import Recruitment
        from app.human.models.candidate import Candidate
        from app.human.models.application import Application

        r = Recruitment()
        db.add(r)
        db.flush()
        c = Candidate(email="pool@test.com", real_name="人才池")
        db.add(c)
        db.flush()
        a = Application(candidate_id=c.id, recruitment_id=r.id)
        db.add(a)
        db.commit()

        schema = PoolItemRead.model_validate(a)
        assert schema.candidate_email == ""
        assert schema.candidate_name == ""


class TestUnpoolRequest:
    def test_valid(self):
        s = UnpoolRequest(recruitment_id=1)
        assert s.recruitment_id == 1

    def test_zero_id_invalid(self):
        with pytest.raises(ValidationError):
            UnpoolRequest(recruitment_id=0)


class TestConfirmRequest:
    def test_defaults(self):
        s = ConfirmRequest()
        assert s.action == "confirmed"
        assert s.status == "contacted"
        assert s.real_name == ""
        assert s.email == ""


class TestConfirmResponse:
    def test_create(self):
        s = ConfirmResponse(queue_id=1, action="confirmed", talent_id=42)
        assert s.queue_id == 1
        assert s.talent_id == 42

    def test_optional_talent_id(self):
        s = ConfirmResponse(queue_id=1, action="confirmed")
        assert s.talent_id is None


class TestIgnoreRequest:
    def test_default(self):
        s = IgnoreRequest()
        assert s.action == "ignored"
