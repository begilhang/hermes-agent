from hermes_cli.autonomy.final_report import MissionReport, render_final_report


def test_final_report_starts_with_gate_and_contains_required_sections():
    report = render_final_report(
        MissionReport(
            gate="REPAIR",
            mission="Diagnose BookForge Chapter 28.",
            actions=["Read /api/status", "Inspected Chapter 28 review artifact"],
            evidence=["/api/status reachable"],
            repairs=["No mutation performed"],
            changed_files=[],
            verification=["synthetic check passed"],
            quarantined=["risk acceptance"],
            current_state="Chapter 28 remains blocked.",
            next_recommended_mission="Approve bounded engine context-budget fix.",
        )
    )

    assert report.startswith("Gate: REPAIR")
    for section in (
        "Mission:",
        "Autonomous actions completed:",
        "Evidence:",
        "Repairs:",
        "Changed files:",
        "Verification:",
        "Quarantined:",
        "Current state:",
        "Next recommended mission:",
    ):
        assert section in report


def test_final_report_rejects_unknown_gate():
    try:
        render_final_report(MissionReport(gate="ASK", mission="bad"))
    except ValueError as exc:
        assert "unsupported gate" in str(exc)
    else:
        raise AssertionError("expected ValueError")
