import json


def test_route_preflight_reports_global_orchestrator_route(monkeypatch, tmp_path):
    from hermes_cli.route_preflight import build_route_preflight_packet

    profile_home = tmp_path / "profiles" / "global_orchestrator"
    profile_home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(profile_home))

    cfg = {
        "model": {
            "default": "qwen36-27b-omlx-production",
            "provider": "custom:omlx-local",
            "base_url": "http://127.0.0.1:8001/v1",
        },
        "fallback_providers": [
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
        ],
    }

    packet_text = build_route_preflight_packet(cfg)
    packet = json.loads(packet_text)

    assert packet["route_gate"] == "ROUTE_PASS"
    assert packet["effective_profile"] == "global_orchestrator"
    assert packet["effective_model"] == "qwen36-27b-omlx-production"
    assert packet["effective_provider"] == "custom:omlx-local"
    assert packet["effective_base_url"] == "http://127.0.0.1:8001/v1"
    assert packet["fallback_chain"] == ["openrouter_deepseek", "direct_deepseek"]
    assert packet["forbidden_fallback_detected"] is False
    assert packet["secrets_printed"] is False
    assert packet["surface"] == "cli"


def test_route_preflight_fails_closed_on_openai_codex_fallback(monkeypatch, tmp_path):
    from hermes_cli.route_preflight import build_route_preflight_packet

    profile_home = tmp_path / "profiles" / "global_orchestrator"
    profile_home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(profile_home))

    cfg = {
        "model": {
            "default": "qwen36-27b-omlx-production",
            "provider": "custom:omlx-local",
            "base_url": "http://127.0.0.1:8001/v1",
        },
        "fallback_providers": [
            {"provider": "openai-codex", "model": "gpt-5.5"},
        ],
    }

    packet = json.loads(build_route_preflight_packet(cfg))

    assert packet["route_gate"] == "ROUTE_FAIL"
    assert packet["forbidden_fallback_detected"] is True
    assert packet["secrets_printed"] is False
    assert packet["surface"] == "cli"
