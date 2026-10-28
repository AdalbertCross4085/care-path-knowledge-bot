import re

from .models import OperationalNotification


_IDENTIFIERS = (
    re.compile(r"\bMRN\s*[:#-]?\s*[A-Za-z0-9-]+\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b"),
)


def patient_safe_notification(message: str) -> OperationalNotification:
    """Remove direct identifiers before an operational note can be emitted."""
    sanitized = message
    for pattern in _IDENTIFIERS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return OperationalNotification(message=sanitized, patient_safe=True)
