"""Keyword-based email classifier for recruitment emails."""


_RULES: list[tuple[list[str], str]] = [
    (["应聘", "求职"], "contacted"),
    (["笔试答案", "答题", "试卷"], "exam_received"),
    (["面试感谢", "面试反馈", "面试结果"], "interview"),
    (["放弃", "退出", "辞职", "离职"], "closed"),
]

_HEADHUNTER_DOMAINS = ["liepin", "zhaopin", "51job", "hunter", "猎聘"]
_HEADHUNTER_BODY_KEYWORDS = ["推荐候选人"]


def classify(subject: str, body: str = "", sender_email: str = "") -> tuple[str | None, str]:
    """Classify a recruitment email.

    Returns (suggested_status, confidence).
    """
    for keywords, status in _RULES:
        for kw in keywords:
            if kw in subject:
                return (status, "high")

    if sender_email:
        domain = sender_email.split("@")[-1].lower() if "@" in sender_email else ""
        for hd in _HEADHUNTER_DOMAINS:
            if hd in domain:
                return ("contacted", "low")

    for kw in _HEADHUNTER_BODY_KEYWORDS:
        if kw in body:
            return ("contacted", "low")

    return (None, "low")
