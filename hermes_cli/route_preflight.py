"""Deterministic route-preflight packets for orchestration profiles.

This module intentionally reports routing metadata from local Hermes config.
It must not call an LLM, read secrets, inspect project evidence, or perform
runtime work. The Brain CEO uses this packet to decide whether delegation is
safe before asking a worker to gather domain evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hermes_cli.fallback_config import get_fallback_chain


FORBIDDEN_TOOL_WORKER_PROVIDERS = {"openai-codex"}
FORBIDDEN_TOOL_WORKER_MODELS = {"gpt-5.5", "openai/gpt-5.5"}


def _profile_name() -> str:
    home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
    if home.parent.name == "profiles" and home.name:
        return home.name
    return "default"


def _model_cfg(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("model") or {}
    if isinstance(raw, str):
        return {"default": raw}
    if isinstance(raw, dict):
        return raw
    return {}


def _provider_cfg(config: dict[str, Any], provider: str) -> dict[str, Any]:
    providers = config.get("providers")
    if not isinstance(providers, dict):
        return {}
    key = provider.split(":", 1)[1] if provider.startswith("custom:") else provider
    raw = providers.get(key) or providers.get(provider) or {}
    return raw if isinstance(raw, dict) else {}


def _effective_base_url(config: dict[str, Any], model_cfg: dict[str, Any], provider: str) -> str:
    explicit = str(model_cfg.get("base_url") or "").strip().rstrip("/")
    if explicit:
        return explicit
    provider_cfg = _provider_cfg(config, provider)
    for key in ("base_url", "api"):
        value = str(provider_cfg.get(key) or "").strip().rstrip("/")
        if value:
            return value
    return ""


def _fallback_label(entry: dict[str, Any]) -> str:
    provider = str(entry.get("provider") or "").strip().lower()
    model = str(entry.get("model") or "").strip().lower()
    if provider == "openrouter" and "deepseek" in model:
        return "openrouter_deepseek"
    if provider == "deepseek":
        return "direct_deepseek"
    safe_provider = provider.replace(":", "_").replace("/", "_") or "unknown_provider"
    safe_model = model.replace(":", "_").replace("/", "_") or "unknown_model"
    return f"{safe_provider}_{safe_model}"


def _has_forbidden_route(
    model: str,
    provider: str,
    fallback_entries: list[dict[str, Any]] | None = None,
) -> bool:
    provider_l = provider.strip().lower()
    model_l = model.strip().lower()
    if provider_l in FORBIDDEN_TOOL_WORKER_PROVIDERS or model_l in FORBIDDEN_TOOL_WORKER_MODELS:
        return True
    for entry in fallback_entries or []:
        entry_provider = str(entry.get("provider") or "").strip().lower()
        entry_model = str(entry.get("model") or "").strip().lower()
        if entry_provider in FORBIDDEN_TOOL_WORKER_PROVIDERS:
            return True
        if entry_model in FORBIDDEN_TOOL_WORKER_MODELS:
            return True
    return False


def _route_fail(
    reason: str,
    *,
    forbidden_fallback_detected: bool = False,
    surface: str = "unknown",
) -> str:
    return json.dumps(
        {
            "route_gate": "ROUTE_FAIL",
            "failure_reason": reason,
            "forbidden_fallback_detected": bool(forbidden_fallback_detected),
            "secrets_printed": False,
            "surface": str(surface or "unknown").strip() or "unknown",
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def build_route_preflight_packet_for_route(
    *,
    effective_profile: str,
    effective_model: str,
    effective_provider: str,
    effective_base_url: str,
    fallback_entries: list[dict[str, Any]] | None = None,
    surface: str = "unknown",
) -> str:
    """Return a compact JSON route packet for an already-resolved route."""

    effective_profile = str(effective_profile or "").strip()
    effective_model = str(effective_model or "").strip()
    effective_provider = str(effective_provider or "").strip()
    effective_base_url = str(effective_base_url or "").strip().rstrip("/")
    surface = str(surface or "unknown").strip() or "unknown"
    fallback_entries = list(fallback_entries or [])
    fallback_chain = [_fallback_label(entry) for entry in fallback_entries]
    forbidden = _has_forbidden_route(
        effective_model,
        effective_provider,
        fallback_entries,
    )

    missing = [
        name
        for name, value in (
            ("effective_profile", effective_profile),
            ("effective_model", effective_model),
            ("effective_provider", effective_provider),
            ("effective_base_url", effective_base_url),
        )
        if not value
    ]
    if missing:
        return _route_fail(
            f"missing required route field(s): {', '.join(missing)}",
            forbidden_fallback_detected=forbidden,
            surface=surface,
        )
    if fallback_chain[:2] != ["openrouter_deepseek", "direct_deepseek"]:
        return _route_fail(
            "fallback chain must start with openrouter_deepseek then direct_deepseek",
            forbidden_fallback_detected=forbidden,
            surface=surface,
        )
    if forbidden:
        return _route_fail(
            "forbidden GPT-5.5/OpenAI-Codex tool-worker fallback detected",
            forbidden_fallback_detected=True,
            surface=surface,
        )

    return json.dumps(
        {
            "route_gate": "ROUTE_PASS",
            "effective_profile": effective_profile,
            "effective_model": effective_model,
            "effective_provider": effective_provider,
            "effective_base_url": effective_base_url,
            "fallback_chain": fallback_chain,
            "forbidden_fallback_detected": False,
            "secrets_printed": False,
            "surface": surface,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def build_route_preflight_packet(config: dict[str, Any] | None, *, surface: str = "cli") -> str:
    """Return a compact JSON route packet for the current Hermes profile."""

    config = config or {}
    model_cfg = _model_cfg(config)
    effective_provider = str(model_cfg.get("provider") or "").strip()
    return build_route_preflight_packet_for_route(
        effective_profile=_profile_name(),
        effective_model=str(model_cfg.get("default") or model_cfg.get("model") or "").strip(),
        effective_provider=effective_provider,
        effective_base_url=_effective_base_url(config, model_cfg, effective_provider),
        fallback_entries=get_fallback_chain(config),
        surface=surface,
    )
