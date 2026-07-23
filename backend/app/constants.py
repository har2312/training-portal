"""
Shared domain constants: designation hierarchy, training topics, and the
date-based schedule status helper. Single source of truth for both the ML
engine and the API layer.
"""
from datetime import date

# Strict decreasing hierarchy (index 0 = most senior).
DESIGNATION_HIERARCHY = [
    "ADG", "DDG", "Director", "DD", "AD", "AE",
    "SEA", "EA", "Senior Tech", "Tech", "Helper",
]
_RANK = {d: i for i, d in enumerate(DESIGNATION_HIERARCHY)}
_UNKNOWN_RANK = len(DESIGNATION_HIERARCHY)  # unknown designations sort last


def designation_rank(designation: str) -> int:
    """Lower = more senior. Unknown designations sort to the bottom."""
    return _RANK.get(designation, _UNKNOWN_RANK)


def meets_threshold(designation: str, min_designation: str | None) -> bool:
    """
    True if `designation` is at or above `min_designation` ("X & above").
    'Above' = more senior = lower rank index. No threshold => everyone passes.
    """
    if not min_designation:
        return True
    return designation_rank(designation) <= designation_rank(min_designation)


# Training topics used across the platform.
TOPICS = ["AI", "Signal", "Content", "Administration", "Awareness"]

# Topics considered "technical" (used by The Oracle for skill-gap phrasing).
TECHNICAL_TOPICS = {"AI", "Signal"}


def schedule_status(from_date: str | None, to_date: str | None, today: date | None = None) -> str:
    """Classify a workshop as Upcoming / Ongoing / Completed from its ISO dates."""
    today = today or date.today()
    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except (TypeError, ValueError):
        return "Upcoming"
    if end < today:
        return "Completed"
    if start > today:
        return "Upcoming"
    return "Ongoing"
