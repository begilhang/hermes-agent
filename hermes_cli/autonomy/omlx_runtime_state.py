from __future__ import annotations

from typing import Any


def build_omlx_runtime_state(
    *,
    health: dict[str, Any] | None,
    requested_route_model: str = "",
    models: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    health = health if isinstance(health, dict) else {}
    pool = health.get("engine_pool") if isinstance(health.get("engine_pool"), dict) else {}
    configured_default = str(health.get("default_model") or "").strip()
    loaded_model = _loaded_model_name(health, pool, models)
    requested = str(requested_route_model or "").strip()
    return {
        "configured_default_model": configured_default or "UNKNOWN",
        "requested_route_model": requested or "UNKNOWN",
        "loaded_model_name": loaded_model or "UNKNOWN",
        "loaded_count": pool.get("loaded_count"),
        "current_model_memory": pool.get("current_model_memory"),
        "final_ceiling": pool.get("final_ceiling"),
        "default_label_mismatch_possible": _mismatch_possible(
            configured_default,
            loaded_model,
            requested,
            pool.get("loaded_count"),
        ),
    }


def _loaded_model_name(
    health: dict[str, Any],
    pool: dict[str, Any],
    models: dict[str, Any] | list[Any] | None,
) -> str:
    for source in (pool, health):
        for key in ("loaded_model", "current_model", "active_model", "loaded_model_name"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(models, dict):
        candidates = models.get("data") or models.get("models") or []
    elif isinstance(models, list):
        candidates = models
    else:
        candidates = []
    loaded = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        if item.get("loaded") is True or item.get("is_loaded") is True:
            name = item.get("id") or item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip():
                loaded.append(name.strip())
    if len(loaded) == 1:
        return loaded[0]
    return ""


def _mismatch_possible(
    configured_default: str,
    loaded_model: str,
    requested_route_model: str,
    loaded_count: Any,
) -> bool:
    if loaded_count in (0, "0", None):
        return False
    if not loaded_model:
        return bool(requested_route_model and configured_default and requested_route_model != configured_default)
    if configured_default and loaded_model and configured_default != loaded_model:
        return True
    if requested_route_model and loaded_model and requested_route_model != loaded_model:
        return True
    return False

