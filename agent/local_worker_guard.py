"""Shared local-worker guardrails for CEO context preservation."""

from __future__ import annotations

import json
from typing import Any, Optional


def _truthy_config_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "y"}
    return False


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    return out if out > 0 else default


def is_subagent_task(task_id: str | None) -> bool:
    raw = str(task_id or "")
    return raw.startswith("sa-") or raw.startswith("subagent-")


def local_worker_enforcement_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
    except Exception:
        return {}

    raw = cfg.get("local_worker_enforcement")
    if not isinstance(raw, dict):
        return {}
    if not _truthy_config_value(raw.get("enabled", False)):
        return {}
    return raw


def local_worker_block_message(kind: str, detail: str) -> str:
    return (
        f"CHEAP_LOCAL_WORKER_REQUIRED: broad parent {kind} is blocked for this profile."
        f" {detail} Route source inspection, status reconstruction, repo/vault/log search,"
        " memory/session comparison, routine critique, or checklist generation through a"
        " lane-scoped local delegate_task worker first. The CEO parent should read only"
        " the compact worker report, then decide, verify, give feedback, or escalate."
        " Narrow deterministic metadata checks remain allowed; broad discovery belongs"
        " in disposable worker context."
    )


def _session_search_block_payload(message: str, *, function_args: dict[str, Any]) -> str:
    return json.dumps(
        {
            "success": False,
            "error": message,
            "code": "CHEAP_LOCAL_WORKER_REQUIRED",
            "tool": "session_search",
            "blocked_args": {
                "query": function_args.get("query"),
                "limit": function_args.get("limit"),
                "session_id": function_args.get("session_id"),
                "around_message_id": function_args.get("around_message_id"),
                "window": function_args.get("window"),
                "profile": function_args.get("profile"),
            },
            "next_action": "Create a lane-scoped local delegate_task worker to reconstruct/search the session and return a compact report.",
        },
        ensure_ascii=False,
    )


def session_search_context_block(
    function_args: dict[str, Any],
    *,
    task_id: str | None,
    result: Any | None = None,
) -> Optional[str]:
    """Block broad parent session recall before it enters CEO context.

    ``session_search`` is an internal agent-loop tool, so it bypasses the
    normal ``model_tools.handle_function_call`` guard path. This helper gives
    both agent-loop executors the same parent/subagent distinction used by the
    file, terminal, and execute_code guards.
    """
    if is_subagent_task(task_id):
        return None

    guard = local_worker_enforcement_config()
    if not guard:
        return None

    policy = guard.get("ceo_context_preservation") or {}
    if not isinstance(policy, dict) or not _truthy_config_value(policy.get("enabled", False)):
        return None

    if _truthy_config_value(function_args.get("local_worker_bypass")):
        return None

    max_window = _coerce_positive_int(policy.get("max_parent_session_search_window"), 5)
    max_chars = _coerce_positive_int(policy.get("max_parent_session_search_chars"), 12000)
    max_limit = _coerce_positive_int(policy.get("max_parent_session_search_limit"), 3)

    session_id = function_args.get("session_id")
    around_message_id = function_args.get("around_message_id")
    if isinstance(session_id, str) and session_id.strip() and around_message_id is None:
        return _session_search_block_payload(
            local_worker_block_message(
                "session_search read",
                (
                    "Full-session reads by the CEO parent are blocked. Use a local"
                    " Research/Intelligence or project-continuation worker to read the"
                    " session and return a compact checkpoint/handoff report. For a"
                    " narrow anchored excerpt, use around_message_id with a small window."
                ),
            ),
            function_args=function_args,
        )

    try:
        requested_window = int(function_args.get("window", 5))
    except (TypeError, ValueError):
        requested_window = 5
    if around_message_id is not None and requested_window > max_window:
        return _session_search_block_payload(
            local_worker_block_message(
                "session_search scroll",
                (
                    f"Requested window={requested_window}; parent window limit is"
                    f" {max_window}. Delegate broader session reconstruction to a local"
                    " worker."
                ),
            ),
            function_args=function_args,
        )

    try:
        requested_limit = int(function_args.get("limit", 3))
    except (TypeError, ValueError):
        requested_limit = 3
    if requested_limit > max_limit:
        return _session_search_block_payload(
            local_worker_block_message(
                "session_search discovery",
                (
                    f"Requested limit={requested_limit}; parent discovery limit is"
                    f" {max_limit}. Delegate broader memory/session search to a local worker."
                ),
            ),
            function_args=function_args,
        )

    if result is None:
        return None

    text = result if isinstance(result, str) else str(result)
    if len(text) <= max_chars:
        return None

    return _session_search_block_payload(
        local_worker_block_message(
            "session_search output",
            (
                f"session_search returned {len(text)} characters; parent output limit is"
                f" {max_chars}. Delegate session reconstruction/search to a local worker"
                " and ask for a compact summary with evidence references."
            ),
        ),
        function_args=function_args,
    )
