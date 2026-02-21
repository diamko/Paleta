import re


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str | None) -> str:
    if not value:
        return ""
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        return ""
    return email


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    if not raw:
        return ""

    digits = re.sub(r"\D", "", raw)
    if not (10 <= len(digits) <= 15):
        return ""

    return f"+{digits}"
