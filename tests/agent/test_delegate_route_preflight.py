import json


class RoutePreflightChild:
    model = "qwen36-27b-omlx-production"
    provider = "custom:omlx-local"
    base_url = "http://127.0.0.1:8001/v1"
    tool_progress_callback = None
    _delegate_role = "leaf"
    _delegate_route_profile = "global_orchestrator"
    _delegate_route_fallback_chain = [
        {
            "provider": "openrouter",
            "model": "deepseek/deepseek-v4-flash",
            "base_url": "https://openrouter.ai/api/v1",
        },
        {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "base_url": "https://api.deepseek.com/v1",
        },
    ]

    def __init__(self):
        self.run_conversation_called = False

    def run_conversation(self, **kwargs):
        self.run_conversation_called = True
        raise AssertionError("route preflight must not call the child model")

    def close(self):
        pass


class PacketChild:
    model = "qwen36-27b-omlx-production"
    provider = "custom:omlx-local"
    base_url = "http://127.0.0.1:8001/v1"
    tool_progress_callback = None
    _delegate_role = "leaf"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.session_prompt_tokens = 0
        self.session_completion_tokens = 0

    def run_conversation(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)

    def get_activity_summary(self):
        return {"api_call_count": len(self.calls)}

    def close(self):
        pass


def test_delegate_route_preflight_returns_packet_without_model_call():
    from tools.delegate_tool import _run_single_child

    child = RoutePreflightChild()

    result = _run_single_child(
        0,
        "Run route preflight only, then stop.",
        child=child,
        parent_agent=None,
    )

    packet = json.loads(result["summary"])
    assert result["status"] == "completed"
    assert result["api_calls"] == 0
    assert result["exit_reason"] == "route_preflight"
    assert child.run_conversation_called is False
    assert packet["route_gate"] == "ROUTE_PASS"
    assert packet["effective_profile"] == "global_orchestrator"
    assert packet["effective_model"] == "qwen36-27b-omlx-production"
    assert packet["effective_provider"] == "custom:omlx-local"
    assert packet["effective_base_url"] == "http://127.0.0.1:8001/v1"
    assert packet["fallback_chain"] == ["openrouter_deepseek", "direct_deepseek"]
    assert packet["forbidden_fallback_detected"] is False
    assert packet["secrets_printed"] is False
    assert packet["surface"] == "delegate_task"


def test_delegate_route_preflight_fails_closed_on_forbidden_worker_fallback():
    from tools.delegate_tool import _run_single_child

    child = RoutePreflightChild()
    child._delegate_route_fallback_chain = [
        {"provider": "openai-codex", "model": "gpt-5.5"},
    ]

    result = _run_single_child(
        0,
        "ROUTE_PREFLIGHT_ONLY. Return only valid JSON.",
        child=child,
        parent_agent=None,
    )

    packet = json.loads(result["summary"])
    assert result["status"] == "failed"
    assert result["api_calls"] == 0
    assert child.run_conversation_called is False
    assert packet["route_gate"] == "ROUTE_FAIL"
    assert packet["forbidden_fallback_detected"] is True
    assert packet["secrets_printed"] is False
    assert packet["surface"] == "delegate_task"


def test_delegate_rejects_invalid_ceo_packet_before_parent_consumes_it():
    from tools.delegate_tool import _run_single_child

    child = PacketChild(
        [
            {
                "final_response": "I will inspect the files and then report back.",
                "completed": True,
                "api_calls": 1,
                "messages": [],
            },
            {
                "final_response": "Still not a packet.",
                "completed": True,
                "api_calls": 1,
                "messages": [],
            },
        ]
    )

    result = _run_single_child(
        0,
        "Produce CEO_DECISION_PACKET only for BookForge Chapter 28 read-only diagnosis.",
        child=child,
        parent_agent=None,
    )

    assert result["status"] == "failed"
    assert result["exit_reason"] == "packet_invalid"
    assert result["api_calls"] == 2
    assert result["summary"] is None
    assert result["packet_gate"]["packet_gate"] == "PACKET_INVALID"
    assert result["packet_gate"]["repair_attempted"] is True
    assert len(child.calls) == 2


def test_delegate_repairs_invalid_ceo_packet_once_and_accepts_valid_packet():
    from tools.delegate_tool import _run_single_child

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
    child = PacketChild(
        [
            {
                "final_response": "I will inspect the files and then report back.",
                "completed": True,
                "api_calls": 1,
                "messages": [],
            },
            {
                "final_response": valid_packet,
                "completed": True,
                "api_calls": 1,
                "messages": [],
            },
        ]
    )

    result = _run_single_child(
        0,
        "Produce CEO_DECISION_PACKET only for BookForge Chapter 28 read-only diagnosis.",
        child=child,
        parent_agent=None,
    )

    assert result["status"] == "completed"
    assert result["exit_reason"] == "completed"
    assert result["api_calls"] == 2
    assert result["summary"] == valid_packet
    assert result["packet_gate"]["packet_gate"] == "PACKET_VALID"
    assert result["packet_gate"]["repair_attempted"] is True
    assert child.calls[1]["user_message"].startswith("REPAIR_PREVIOUS_INVALID_OUTPUT")
