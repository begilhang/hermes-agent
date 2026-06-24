from __future__ import annotations


SECTION_HEADERS = (
    "forbidden:",
    "do not:",
    "hard stops:",
    "still forbidden:",
)


def requested_action_text(text: str) -> str:
    """Return the affirmative/requested part of a mission prompt.

    Users often include a "Forbidden:" or "Do not:" section. Those lines are
    policy boundaries, not requested actions, so action classification should
    not quarantine the whole mission just because the boundary says
    "Do not publish/export".
    """

    raw = text or ""
    lower = raw.lower()
    cut = len(raw)
    for header in SECTION_HEADERS:
        idx = lower.find(header)
        if idx >= 0:
            cut = min(cut, idx)
    return raw[:cut].strip() or raw.strip()

