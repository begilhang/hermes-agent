from __future__ import annotations


def is_autonomous_mission_prompt(prompt: str) -> bool:
    try:
        from hermes_cli.overlay_loader import load_architecture_overlay

        overlay = load_architecture_overlay("autonomy")
        return bool(overlay.is_autonomous_mission_prompt(prompt))
    except Exception:
        pass

    text = (prompt or "").lower()
    stripped = text.strip()
    return (
        stripped.startswith("autonomous_mission:")
        or "autonomous mode" in text
        or "return final report only" in text
        or "final_report_only" in text
    )
