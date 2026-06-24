import json

from hermes_cli.packet_validation import (
    validate_ceo_decision_packet,
    validate_delegated_output,
    validate_route_preflight_packet,
)


def test_valid_ceo_packet_requires_evidence_and_decision_shape():
    packet = """CEO_DECISION_PACKET

Current state:
- BookForge is stopped.

Evidence:
- `/Users/begilhan/Bookforge V2 PublicationForge/docs/runtime/CURRENT_RUNTIME_PACKET.md`
- `http://127.0.0.1:5012/api/status`

Risks:
- Chapter 28 context budget is unresolved.

Recommendation:
- Read-only context-budget repair planning only.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is True
    assert result.code == "PACKET_VALID"


def test_ceo_packet_rejects_planned_tool_narration():
    packet = """CEO_DECISION_PACKET

Current state:
- I will inspect the repo next.

Evidence:
- `/Users/begilhan/Bookforge V2 PublicationForge`

Risks:
- unknown

Recommendation:
- Read-only.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is False
    assert result.code == "PACKET_INVALID"
    assert "planned tool work" in result.reason


def test_ceo_packet_rejects_forbidden_generation_recommendation():
    packet = """CEO_DECISION_PACKET

Current state:
- BookForge is stopped.

Evidence:
- `http://127.0.0.1:5012/api/status`

Risks:
- unknown

Recommendation:
- Resume BookForge generation.

Decision requested:
- APPROVE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is False
    assert result.code == "PACKET_INVALID"
    assert "BookForge generation" in result.reason


def test_ceo_packet_rejects_bookforge_chapter_generation_wording():
    packet = """CEO_DECISION_PACKET

Goal:
- Resume BookForge chapter generation.

Current state:
- BookForge is stopped.

Evidence:
- `http://127.0.0.1:5012/api/status`

Risks:
- unknown

Recommendation:
- Read-only.

Decision requested:
- APPROVE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is False
    assert result.code == "PACKET_INVALID"
    assert "BookForge generation" in result.reason


def test_ceo_packet_rejects_pending_evidence_as_if_it_were_evidence():
    packet = """CEO_DECISION_PACKET

Current state:
- BookForge is stopped.

Evidence:
- `http://127.0.0.1:5012/api/status` — to be polled.

Files/Artifacts Inspected: None yet.

Risks:
- unknown

Recommendation:
- Read-only.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is False
    assert result.code == "PACKET_INVALID"
    assert "pending evidence" in result.reason


def test_route_preflight_rejects_pass_with_blank_required_fields():
    packet = json.dumps(
        {
            "route_gate": "ROUTE_PASS",
            "effective_profile": "global_orchestrator",
            "effective_model": "",
            "effective_provider": "custom:omlx-local",
            "effective_base_url": "http://127.0.0.1:8001/v1",
            "fallback_chain": ["openrouter_deepseek", "direct_deepseek"],
            "forbidden_fallback_detected": False,
            "secrets_printed": False,
            "surface": "delegate_task",
        }
    )

    result = validate_route_preflight_packet(packet)

    assert result.valid is False
    assert result.code == "ROUTE_PACKET_INVALID"
    assert "effective_model" in result.reason


def test_delegated_output_only_applies_ceo_packet_gate_when_goal_requests_it():
    assert validate_delegated_output("summarize this", "loose prose").valid is True
    assert validate_delegated_output("Return CEO_DECISION_PACKET only", "loose prose").valid is False
