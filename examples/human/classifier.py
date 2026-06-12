from dataclasses import dataclass

STATUS_KEYWORDS = {
    "contacted": ["应聘", "求职", "简历", "申请"],
    "exam_sent": ["笔试邀请", "笔试通知", "在线考试"],
    "exam_received": ["笔试答案", "答题", "笔试完成", "提交答卷"],
    "evaluating": ["评估", "审核简历", "简历评估"],
    "interview": ["面试感谢", "面试反馈", "面试安排", "面试邀请"],
    "offer": ["offer", "录用通知", "入职邀请", "薪酬确认"],
    "closed": ["放弃", "退出", "拒绝", "不考虑"],
}

@dataclass
class ClassificationResult:
    suggested_status: str | None
    confidence: str
    suggested_position: str | None
    extracted_name: str | None
    extracted_email: str | None
    extracted_phone: str | None

def classify(subject: str, sender_name: str, sender_email: str) -> ClassificationResult:
    subject_lower = subject.lower()
    suggested_status = None; confidence = "low"
    matched_keywords = []
    for status, keywords in STATUS_KEYWORDS.items():
        for kw in keywords:
            if kw in subject_lower:
                matched_keywords.append((status, kw))
    if matched_keywords:
        status_groups = {}
        for s, _ in matched_keywords:
            status_groups[s] = status_groups.get(s, 0) + 1
        suggested_status = max(status_groups, key=status_groups.get)
        confidence = "high" if status_groups[suggested_status] >= 2 else "medium"
    extracted_name = sender_name if sender_name and sender_name != sender_email else None
    return ClassificationResult(suggested_status, confidence, None, extracted_name, sender_email, None)
