import json

from hermes_cli.route_preflight import build_route_preflight_packet


def test_openrouter_deepseek_preflight_fails_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = {
        "model": {
            "default": "deepseek/deepseek-v4-flash",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
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
            {
                "provider": "custom:omlx-local",
                "model": "Qwopus3.6-27B-v2-oQ4-mtp",
                "base_url": "http://127.0.0.1:8001/v1",
            },
        ],
    }

    packet = json.loads(build_route_preflight_packet(cfg, surface="delegate_task"))

    assert packet["route_gate"] == "ROUTE_FAIL"
    assert packet["failure_reason"] == "OPENROUTER_AUTH_MISSING"
    assert packet["secrets_printed"] is False


def test_openrouter_deepseek_preflight_passes_with_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-secret")
    cfg = {
        "model": {
            "default": "deepseek/deepseek-v4-flash",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
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

    packet = json.loads(build_route_preflight_packet(cfg, surface="delegate_task"))

    assert packet["route_gate"] == "ROUTE_PASS"
    assert packet["effective_provider"] == "openrouter"
    assert "sk-or-test-secret" not in json.dumps(packet)

