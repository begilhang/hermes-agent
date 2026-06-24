from __future__ import annotations


def is_autonomous_mission_prompt(prompt: str) -> bool:
    text = (prompt or "").lower()
    stripped = text.strip()
    return (
        stripped.startswith("autonomous_mission:")
        or "autonomous mode" in text
        or "return final report only" in text
        or "final_report_only" in text
    )

