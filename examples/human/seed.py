from datetime import datetime, timedelta
from hashlib import md5
from sqlalchemy import update
from sqlalchemy.orm import Session
from human.models.application import Application
from human.models.candidate import Candidate
from human.models.pending_queue import PendingQueueItem
from human.models.recruitment import Recruitment
from human.models.talent import Talent, TalentStatus

SEED_TRANSITIONS = {
    s: [] for s in ["new", "contacted", "exam_sent", "exam_received", "evaluating", "interview", "offer", "closed"]
}
SEED_TRANSITIONS["contacted"] = ["contacted"]
SEED_TRANSITIONS["exam_sent"] = ["contacted", "exam_sent"]
SEED_TRANSITIONS["exam_received"] = ["contacted", "exam_sent", "exam_received"]
SEED_TRANSITIONS["evaluating"] = ["contacted", "exam_sent", "exam_received", "evaluating"]
SEED_TRANSITIONS["interview"] = ["contacted", "exam_sent", "exam_received", "evaluating", "interview"]
SEED_TRANSITIONS["offer"] = ["contacted", "exam_sent", "exam_received", "evaluating", "interview", "offer"]
SEED_TRANSITIONS["closed"] = ["closed"]

DEMO_TALENTS = [
    ("new", f"张{cn}", f"zhang{i}@demo.local", None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("contacted", f"李{cn}", f"li{i}@demo.local", None if i > 3 else "resume_passed") for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("exam_sent", f"王{cn}", f"wang{i}@demo.local", "taking" if 2 <= i <= 4 else None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("exam_received", f"赵{cn}", f"zhao{i}@demo.local", None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("evaluating", f"孙{cn}", f"sun{i}@demo.local", "exam_passed" if 2 <= i <= 4 else None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("interview", f"周{cn}", f"zhou{i}@demo.local", "interview_passed" if 2 <= i <= 4 else None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("offer", f"吴{cn}", f"wu{i}@demo.local", "accepted" if 2 <= i <= 4 else None) for i, cn in enumerate(["一","二","三","四","五"], 1)
] + [
    ("closed", f"郑{cn}", f"zheng{i}@demo.local", None) for i, cn in enumerate(["一","二","三","四","五"], 1)
]

QUALITY_MAP = {"李二": "excellent", "李三": "excellent", "李四": "excellent",
               "孙二": "excellent", "孙三": "excellent", "周子": "excellent",
               "吴二": "excellent", "吴三": "excellent", "张五": "excellent"}

def build_transition_chain(target: str) -> list[str]:
    return SEED_TRANSITIONS[target]

def seed_data(db: Session) -> None:
    import human.models  # noqa: F401
    r = Recruitment()
    db.add(r); db.flush()

    for target_status, name, email, sub_stage in DEMO_TALENTS:
        t = Talent(recruitment_id=r.id, email=email, real_name=name)
        db.add(t); db.flush()
        for s in build_transition_chain(target_status):
            t.status = TalentStatus(s); db.flush()
        t.sub_stage = sub_stage
        t.quality = QUALITY_MAP.get(name, "normal")
        stage_map = {"exam_sent": {"contacted": "pass"}, "exam_received": {"contacted": "pass"},
                     "evaluating": {"contacted": "pass"}, "interview": {"contacted": "pass", "evaluating": "pass"},
                     "offer": {"contacted": "pass", "evaluating": "pass", "interview": "pass"}}
        t.stage_results = stage_map.get(target_status); db.flush()
    db.commit()

    status_age = {"new": 0, "contacted": 2, "exam_sent": 5, "exam_received": 8,
                  "evaluating": 12, "interview": 15, "offer": 20, "closed": 25}
    for target_status, name, email, _ in DEMO_TALENTS:
        days = status_age[target_status]
        if days > 0:
            db.execute(update(Talent).where(Talent.email == email).values(updated_at=datetime.utcnow() - timedelta(days=days)))
    db.commit()

    email_to_candidate = {}
    for target_status, name, email, _ in DEMO_TALENTS:
        if email not in email_to_candidate:
            c = Candidate(email=email, real_name=name); db.add(c); db.flush()
            email_to_candidate[email] = c

    for target_status, name, email, sub_stage in DEMO_TALENTS:
        talent = db.query(Talent).filter(Talent.email == email).first()
        if talent:
            a = Application(candidate_id=email_to_candidate[email].id, recruitment_id=r.id,
                           status=talent.status, sub_stage=talent.sub_stage, quality=talent.quality,
                           stage_results=talent.stage_results, source="manual_seed")
            db.add(a); db.flush()

    zhang3 = email_to_candidate.get("zhang3@demo.local")
    if zhang3:
        db.add(Application(candidate_id=zhang3.id, recruitment_id=r.id, status=TalentStatus.NEW,
                          source="manual_seed", pooled_at=datetime.utcnow()))
    wang5 = email_to_candidate.get("wang5@demo.local")
    if wang5:
        db.add(Application(candidate_id=wang5.id, recruitment_id=r.id, status=TalentStatus.EXAM_SENT, source="manual_seed"))
    db.commit()

    from human.classifier import classify
    from human.demo import get_demo_emails
    for email in get_demo_emails():
        result = classify(email.subject, email.sender_name, email.sender_email)
        qi = PendingQueueItem(
            message_id=md5(email.subject.encode()).hexdigest()[:16],
            subject=email.subject, sender_name=email.sender_name,
            sender_email=email.sender_email,
            suggested_status=result.suggested_status, confidence=result.confidence,
        )
        db.add(qi)
    db.commit()
