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
- `/Users/begilhan/Bookforge V2 PublicationForge/docs/runtime/CURRENT_RUNTIME_PACKET.md` — reachable; packet says worker idle.
- `http://127.0.0.1:5012/api/status` — reachable; response reports Chapter 28 failed.

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


def test_ceo_packet_rejects_citations_without_concrete_observations():
    packet = """CEO_DECISION_PACKET

Current state:
- BookForge needs diagnosis.

Evidence:
- `/Users/begilhan/Documents/Private documents/sharedmemory/Bookforge/00 Current Status/00 START HERE - Current Hermes BookForge Status.md`
- `http://127.0.0.1:5012/api/status`
- `http://127.0.0.1:5012/api/queue`

Chapter 28 context-budget diagnosis:
- Context budget needs analysis.

Risks:
- unknown

Recommendation:
- Prepare repair planning later.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is False
    assert result.code == "PACKET_INVALID"
    assert "concrete evidence observation" in result.reason


def test_ceo_packet_accepts_access_failed_as_concrete_evidence_status():
    packet = """CEO_DECISION_PACKET

Current state:
- BookForge status cannot be fully verified from the worker.

Evidence:
- `http://127.0.0.1:5012/api/status` — ACCESS_FAILED: local endpoint blocked from worker network boundary.
- `http://127.0.0.1:5012/api/queue` — ACCESS_FAILED: local endpoint blocked from worker network boundary.

Risks:
- status remains unverified.

Recommendation:
- Request narrow host-side status check.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_ceo_decision_packet(packet)

    assert result.valid is True
    assert result.code == "PACKET_VALID"


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


def test_route_json_is_valid_only_for_explicit_route_preflight_only_goal():
    route_json = json.dumps(
        {
            "route_gate": "ROUTE_PASS",
            "effective_profile": "global_orchestrator",
            "effective_model": "deepseek/deepseek-v4-flash",
            "effective_provider": "openrouter",
            "effective_base_url": "https://openrouter.ai/api/v1",
            "fallback_chain": ["openrouter_deepseek", "direct_deepseek"],
            "forbidden_fallback_detected": False,
            "secrets_printed": False,
            "surface": "delegate_task",
        }
    )

    route_result = validate_delegated_output(
        "ROUTE_PREFLIGHT_ONLY. Return only valid JSON.",
        route_json,
    )
    packet_result = validate_delegated_output(
        "Run route preflight first, then produce CEO_DECISION_PACKET for BookForge Chapter 28.",
        route_json,
    )

    assert route_result.valid is True
    assert route_result.code == "ROUTE_PACKET_VALID"
    assert packet_result.valid is False
    assert packet_result.code == "PACKET_INVALID"
    assert "route preflight JSON" in packet_result.reason


def test_ceo_packet_goal_wins_over_route_preflight_wording():
    valid_packet = """CEO_DECISION_PACKET

Current state:
- BookForge is stopped.

Evidence:
- `http://127.0.0.1:5012/api/status` — reachable; response reports Chapter 28 failed.

Risks:
- Chapter 28 context budget is unresolved.

Recommendation:
- Read-only context-budget repair planning only.

Decision requested:
- REQUEST_MORE_EVIDENCE
"""

    result = validate_delegated_output(
        "After route preflight, produce CEO_DECISION_PACKET for Chapter 28.",
        valid_packet,
    )

    assert result.valid is True
    assert result.code == "PACKET_VALID"
