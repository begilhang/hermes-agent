from __future__ import annotations

from dataclasses import dataclass, field


VALID_GATES = {"PASS", "REPAIR", "QUARANTINED"}


@dataclass(frozen=True)
class MissionReport:
    gate: str
    mission: str
    actions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    quarantined: list[str] = field(default_factory=list)
    current_state: str = ""
    next_recommended_mission: str = ""


def render_final_report(report: MissionReport) -> str:
    gate = report.gate.upper().strip()
    if gate not in VALID_GATES:
        raise ValueError(f"unsupported gate: {report.gate}")
    sections = [
        f"Gate: {gate}",
        "",
        "Mission:",
        report.mission or "(not recorded)",
        "",
        "Autonomous actions completed:",
        _render_list(report.actions),
        "",
        "Evidence:",
        _render_list(report.evidence),
        "",
        "Repairs:",
        _render_list(report.repairs),
        "",
        "Changed files:",
        _render_list(report.changed_files),
        "",
        "Verification:",
        _render_list(report.verification),
        "",
        "Quarantined:",
        _render_list(report.quarantined),
        "",
        "Current state:",
        report.current_state or "(unknown)",
        "",
        "Next recommended mission:",
        report.next_recommended_mission or "(none)",
    ]
    return "\n".join(sections).rstrip() + "\n"


def _render_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)
