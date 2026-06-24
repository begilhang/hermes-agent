import json

import pytest


@pytest.mark.parametrize("surface", ["cli", "tui", "dashboard"])
def test_run_conversation_route_preflight_is_deterministic_without_api(
    monkeypatch, tmp_path, surface
):
    from agent.conversation_loop import run_conversation

    profile_home = tmp_path / "profiles" / "global_orchestrator"
    profile_home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(profile_home))

    class Agent:
        model = "qwen36-27b-omlx-production"
        provider = "custom:omlx-local"
        base_url = "http://127.0.0.1:8001/v1"
        platform = surface
        _fallback_chain = [
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

    result = run_conversation(Agent(), "ROUTE_PREFLIGHT_ONLY. Return only valid JSON.")
    packet = json.loads(result["final_response"])

    assert result["completed"] is True
    assert result["api_calls"] == 0
    assert result["exit_reason"] == "route_preflight"
    assert packet["route_gate"] == "ROUTE_PASS"
    assert packet["effective_profile"] == "global_orchestrator"
    assert packet["effective_model"] == "qwen36-27b-omlx-production"
    assert packet["effective_provider"] == "custom:omlx-local"
    assert packet["effective_base_url"] == "http://127.0.0.1:8001/v1"
    assert packet["fallback_chain"] == ["openrouter_deepseek", "direct_deepseek"]
    assert packet["forbidden_fallback_detected"] is False
    assert packet["secrets_printed"] is False
    assert packet["surface"] == surface
