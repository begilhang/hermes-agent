from hermes_cli.autonomy.action_classifier import classify_action
from hermes_cli.autonomy.policy import (
    AutonomyDecision,
    create_mission_envelope,
    default_contract,
)


def test_create_mission_envelope_defaults_to_final_only_autonomy():
    envelope = create_mission_envelope(
        "Diagnose BookForge Chapter 28 context-budget failure."
    )

    assert envelope.goal == "Diagnose BookForge Chapter 28 context-budget failure."
    assert envelope.mode == "autonomous"
    assert envelope.reporting == "final_only"
    assert "read_only_inspection" in envelope.auto_allowed
    assert "risk_acceptance" in envelope.quarantine
    assert envelope.final_output == ["PASS", "REPAIR", "QUARANTINED"]


def test_action_classifier_allows_read_only_planning_and_tests():
    contract = default_contract()

    assert classify_action("read /api/status", contract).decision is AutonomyDecision.AUTO
    assert classify_action("produce repair plan", contract).action_class == "A2"
    assert classify_action("run pytest smoke checks", contract).action_class == "A3"


def test_action_classifier_allows_bounded_local_fix_with_backup():
    contract = default_contract()
    action = classify_action("patch local engine config with backup", contract)

    assert action.action_class == "A4"
    assert action.decision is AutonomyDecision.AUTO


def test_action_classifier_quarantines_external_and_risk_actions():
    contract = default_contract()

    deploy = classify_action("deploy to production", contract)
    risk = classify_action("accept risk and bypass AI Reader gate", contract)
    secret = classify_action("change API secret", contract)

    assert deploy.decision is AutonomyDecision.QUARANTINE
    assert risk.decision is AutonomyDecision.QUARANTINE
    assert secret.decision is AutonomyDecision.QUARANTINE


def test_action_classifier_ignores_forbidden_section_as_requested_action():
    contract = default_contract()
    mission = """Goal:
Fix BookForge Chapter 28 context-budget failure.

Forbidden:
- Do not resume generation.
- Do not publish/export.
- Do not accept risk.
"""

    action = classify_action(mission, contract, mission_goal=mission)

    assert action.decision is AutonomyDecision.AUTO


def test_action_classifier_quarantines_affirmative_publish_request():
    contract = default_contract()
    action = classify_action(
        "Fix BookForge Chapter 28 and publish/export when done.",
        contract,
        mission_goal="Fix BookForge Chapter 28 and publish/export when done.",
    )

    assert action.decision is AutonomyDecision.QUARANTINE


def test_action_classifier_quarantines_chapter_15_unless_explicitly_included():
    contract = default_contract()

    implicit = classify_action("recover chapter 15", contract)
    explicit = classify_action(
        "recover chapter 15",
        contract,
        mission_goal="Autonomously recover chapter 15.",
    )

    assert implicit.decision is AutonomyDecision.QUARANTINE
    assert explicit.decision is AutonomyDecision.AUTO
