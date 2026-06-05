"""Seed data constants for demo/testing."""
from datetime import datetime, timedelta
from hashlib import md5

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.human.models.application import Application
from app.human.models.candidate import Candidate
from app.human.models.pending_queue import PendingQueueItem
from app.human.models.recruitment import Recruitment
from app.human.models.talent import Talent, TalentStatus

SEED_TRANSITIONS = {
    "new": [],
    "contacted": ["contacted"],
    "exam_sent": ["contacted", "exam_sent"],
    "exam_received": ["contacted", "exam_sent", "exam_received"],
    "evaluating": ["contacted", "exam_sent", "exam_received", "evaluating"],
    "interview": ["contacted", "exam_sent", "exam_received", "evaluating", "interview"],
    "offer": ["contacted", "exam_sent", "exam_received", "evaluating", "interview", "offer"],
    "closed": ["closed"],
}

DEMO_TALENTS = [
    ("new", "张一", "zhang1@demo.local", None),
    ("new", "张二", "zhang2@demo.local", None),
    ("new", "张三", "zhang3@demo.local", None),
    ("new", "张四", "zhang4@demo.local", None),
    ("new", "张五", "zhang5@demo.local", None),
    ("contacted", "李一", "li1@demo.local", None),
    ("contacted", "李二", "li2@demo.local", "resume_passed"),
    ("contacted", "李三", "li3@demo.local", "resume_passed"),
    ("contacted", "李四", "li4@demo.local", "resume_passed"),
    ("contacted", "李五", "li5@demo.local", None),
    ("exam_sent", "王一", "wang1@demo.local", None),
    ("exam_sent", "王二", "wang2@demo.local", "taking"),
    ("exam_sent", "王三", "wang3@demo.local", "taking"),
    ("exam_sent", "王四", "wang4@demo.local", "taking"),
    ("exam_sent", "王五", "wang5@demo.local", None),
    ("exam_received", "赵一", "zhao1@demo.local", None),
    ("exam_received", "赵二", "zhao2@demo.local", None),
    ("exam_received", "赵三", "zhao3@demo.local", None),
    ("exam_received", "赵四", "zhao4@demo.local", None),
    ("exam_received", "赵五", "zhao5@demo.local", None),
    ("evaluating", "孙一", "sun1@demo.local", None),
    ("evaluating", "孙二", "sun2@demo.local", "exam_passed"),
    ("evaluating", "孙三", "sun3@demo.local", "exam_passed"),
    ("evaluating", "孙四", "sun4@demo.local", "exam_passed"),
    ("evaluating", "孙五", "sun5@demo.local", None),
    ("interview", "周一", "zhou1@demo.local", None),
    ("interview", "周子", "zhou2@demo.local", "interview_passed"),
    ("interview", "周三", "zhou3@demo.local", "interview_passed"),
    ("interview", "周四", "zhou4@demo.local", "interview_passed"),
    ("interview", "周五", "zhou5@demo.local", None),
    ("offer", "吴一", "wu1@demo.local", None),
    ("offer", "吴二", "wu2@demo.local", "accepted"),
    ("offer", "吴三", "wu3@demo.local", "accepted"),
    ("offer", "吴四", "wu4@demo.local", "accepted"),
    ("offer", "吴五", "wu5@demo.local", None),
    ("closed", "郑一", "zheng1@demo.local", None),
    ("closed", "郑二", "zheng2@demo.local", None),
    ("closed", "郑三", "zheng3@demo.local", None),
    ("closed", "郑四", "zheng4@demo.local", None),
    ("closed", "郑五", "zheng5@demo.local", None),
]

QUALITY_MAP = {
    "李二": "excellent", "李三": "excellent", "李四": "excellent",
    "孙二": "excellent", "孙三": "excellent",
    "周子": "excellent",
    "吴二": "excellent", "吴三": "excellent",
    "张五": "excellent",
}

DEMO_EMAILS = [
    {"subject": "求职申请 - 前端开发", "sender_name": "王小明", "sender_email": "wxm@demo.local"},
    {"subject": "简历: 3年Python后端经验", "sender_name": "李芳", "sender_email": "lifang@demo.local"},
    {"subject": "应聘产品经理岗位", "sender_name": "赵磊", "sender_email": "zhaolei@demo.local"},
    {"subject": "高级Java开发求职", "sender_name": "陈静", "sender_email": "chenjing@demo.local"},
    {"subject": "【求职】数据分析师", "sender_name": "刘洋", "sender_email": "liuyang@demo.local"},
    {"subject": "UI设计师求职作品集", "sender_name": "周婷", "sender_email": "zhouting@demo.local"},
    {"subject": "寻求前端实习机会", "sender_name": "林小华", "sender_email": "linxh@demo.local"},
    {"subject": "DevOps工程师求职", "sender_name": "黄伟", "sender_email": "huangwei@demo.local"},
    {"subject": "测试工程师简历投递", "sender_name": "孙磊", "sender_email": "sunlei@demo.local"},
    {"subject": "市场运营专员求职", "sender_name": "张薇", "sender_email": "zhangwei@demo.local"},
]


def build_transition_chain(target: str) -> list[str]:
    """从 new 走到 target 的合法路径（不含 new 自身）。"""
    return SEED_TRANSITIONS[target]


def seed_data(db: Session) -> None:
    """Populate the database with demo talents and pending queue items."""
    import app.human.models  # noqa: F401

    r = Recruitment()
    db.add(r)
    db.flush()

    for target_status, name, email, sub_stage in DEMO_TALENTS:
        t = Talent(recruitment_id=r.id, email=email, real_name=name)
        db.add(t)
        db.flush()
        for s in build_transition_chain(target_status):
            t.status = TalentStatus(s)
            db.flush()
        t.sub_stage = sub_stage
        t.quality = QUALITY_MAP.get(name, "normal")
        stage_map = {
            "exam_sent": {"contacted": "pass"},
            "exam_received": {"contacted": "pass"},
            "evaluating": {"contacted": "pass"},
            "interview": {"contacted": "pass", "evaluating": "pass"},
            "offer": {"contacted": "pass", "evaluating": "pass", "interview": "pass"},
        }
        t.stage_results = stage_map.get(target_status)
        db.flush()

    db.commit()

    status_age = {"new": 0, "contacted": 2, "exam_sent": 5, "exam_received": 8,
                  "evaluating": 12, "interview": 15, "offer": 20, "closed": 25}
    for target_status, name, email, _ in DEMO_TALENTS:
        days = status_age[target_status]
        if days > 0:
            past = datetime.utcnow() - timedelta(days=days)
            db.execute(update(Talent).where(Talent.email == email).values(updated_at=past))
    db.commit()

    email_to_candidate = {}
    for target_status, name, email, _ in DEMO_TALENTS:
        if email not in email_to_candidate:
            c = Candidate(email=email, real_name=name)
            db.add(c)
            db.flush()
            email_to_candidate[email] = c

    for target_status, name, email, sub_stage in DEMO_TALENTS:
        talent = db.query(Talent).filter(Talent.email == email).first()
        if talent:
            a = Application(
                candidate_id=email_to_candidate[email].id,
                recruitment_id=r.id,
                status=talent.status,
                sub_stage=talent.sub_stage,
                quality=talent.quality,
                stage_results=talent.stage_results,
                source="manual_seed",
            )
            db.add(a)
            db.flush()

    zhang3 = email_to_candidate.get("zhang3@demo.local")
    if zhang3:
        pooled = Application(
            candidate_id=zhang3.id, recruitment_id=r.id,
            status=TalentStatus.NEW, source="manual_seed",
            pooled_at=datetime.utcnow(),
        )
        db.add(pooled)
        db.flush()

    wang5 = email_to_candidate.get("wang5@demo.local")
    if wang5:
        extra = Application(
            candidate_id=wang5.id, recruitment_id=r.id,
            status=TalentStatus.EXAM_SENT, source="manual_seed",
        )
        db.add(extra)
        db.flush()

    db.commit()

    for email in DEMO_EMAILS:
        qi = PendingQueueItem(
            message_id=md5(email["subject"].encode()).hexdigest()[:16],
            subject=email["subject"],
            sender_name=email["sender_name"],
            sender_email=email["sender_email"],
            suggested_status="contacted",
            confidence="medium",
        )
        db.add(qi)
    db.commit()
