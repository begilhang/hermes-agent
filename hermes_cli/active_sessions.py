"""Cross-process active chat session leases.

The session database records persisted conversations.  This module records
currently open chat surfaces, including idle CLI/TUI sessions that have not
written a transcript row yet.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

try:
    _TUI_ORPHAN_LEASE_TTL_S = float(
        os.environ.get("HERMES_TUI_ORPHAN_LEASE_TTL_S") or 300
    )
except (TypeError, ValueError):
    _TUI_ORPHAN_LEASE_TTL_S = 300.0
_TUI_ORPHAN_LEASE_TTL_S = max(30.0, _TUI_ORPHAN_LEASE_TTL_S)


def coerce_max_concurrent_sessions(value: Any, key: str = "max_concurrent_sessions") -> Optional[int]:
    """Return a positive integer cap, or None when disabled/invalid."""
    if value is None:
        return None
    if isinstance(value, bool):
        logger.warning(
            "Ignoring invalid %s=%r (expected a positive integer; 0/null disables)",
            key,
            value,
        )
        return None
    try:
        if isinstance(value, float):
            if not value.is_integer():
                raise ValueError(value)
            parsed = int(value)
        elif isinstance(value, str):
            parsed = int(value.strip(), 10)
        else:
            parsed = int(value)
    except (TypeError, ValueError):
        logger.warning(
            "Ignoring invalid %s=%r (expected a positive integer; 0/null disables)",
            key,
            value,
        )
        return None
    if parsed <= 0:
        return None
    return parsed


def resolve_max_concurrent_sessions(config: Any) -> Optional[int]:
    """Resolve top-level max_concurrent_sessions with gateway.* fallback."""
    raw: Any = None
    key = "max_concurrent_sessions"
    if isinstance(config, dict):
        if "max_concurrent_sessions" in config:
            raw = config.get("max_concurrent_sessions")
        else:
            gateway_cfg = config.get("gateway")
            if isinstance(gateway_cfg, dict):
                raw = gateway_cfg.get("max_concurrent_sessions")
                key = "gateway.max_concurrent_sessions"
    else:
        raw = getattr(config, "max_concurrent_sessions", None)
    return coerce_max_concurrent_sessions(raw, key=key)


def active_session_limit_message(active_count: int, max_sessions: int) -> str:
    return (
        f"Hermes is at the active session limit ({active_count}/{max_sessions}). "
        "Try again when another session finishes."
    )


def _state_dir() -> Path:
    return Path(get_hermes_home()) / "runtime"


def _state_path() -> Path:
    return _state_dir() / "active_sessions.json"


def _lock_path() -> Path:
    return _state_dir() / "active_sessions.lock"


class _FileLock:
    def __init__(self, path: Path):
        self.path = path
        self._fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a+b")
        if os.name == "nt":
            try:
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
            except Exception as exc:
                self._fh.close()
                self._fh = None
                raise RuntimeError("active session file lock unavailable") from exc
        else:
            try:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            except Exception as exc:
                self._fh.close()
                self._fh = None
                raise RuntimeError("active session file lock unavailable") from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fh is None:
            return
        if os.name == "nt":
            try:
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
        else:
            try:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        try:
            self._fh.close()
        finally:
            self._fh = None


def _read_entries(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    except Exception:
        logger.warning("Ignoring corrupt active session registry at %s", path)
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"entries": entries}, fh, sort_keys=True)
    os.replace(tmp, path)


def _process_start_time(pid: int) -> Optional[float]:
    # Pair pid with process create_time when psutil can read it, so a recycled
    # pid does not keep a stale lease alive indefinitely.
    try:
        import psutil  # type: ignore

        return float(psutil.Process(pid).create_time())
    except Exception:
        return None


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pid_alive(pid: Any, process_start_time: Any = None) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        from gateway.status import _pid_exists

        exists = bool(_pid_exists(pid_int))
    except Exception:
        return False
    if not exists:
        return False
    expected_start = _optional_float(process_start_time)
    if expected_start is None:
        return True
    current_start = _process_start_time(pid_int)
    if current_start is None:
        return True
    return abs(current_start - expected_start) < 0.001


def _live_session_id(entry: dict[str, Any]) -> str:
    metadata = entry.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("live_session_id") or "")


def _tui_surface(entry: dict[str, Any]) -> bool:
    surface = str(entry.get("surface") or "").lower()
    return surface in {"tui", "desktop", "dashboard"} or surface.startswith("tui:")


def _entry_has_live_worker(entry: dict[str, Any]) -> bool:
    metadata = entry.get("metadata")
    if not isinstance(metadata, dict):
        return False
    worker_pid = metadata.get("worker_pid")
    if worker_pid in (None, ""):
        return False
    return _pid_alive(worker_pid, metadata.get("worker_process_start_time"))


def _entry_is_stale_tui_orphan(
    entry: dict[str, Any],
    *,
    now: float,
    live_session_ids: Optional[set[str]] = None,
) -> bool:
    if not _tui_surface(entry):
        return False

    live_session_id = _live_session_id(entry)
    if live_session_ids is not None and live_session_id:
        return live_session_id not in live_session_ids

    metadata = entry.get("metadata")
    if isinstance(metadata, dict) and metadata.get("worker_pid") not in (None, ""):
        return not _entry_has_live_worker(entry)

    updated_at = _optional_float(entry.get("updated_at"))
    if updated_at is None:
        updated_at = _optional_float(entry.get("started_at"))
    if updated_at is None:
        return True
    return (now - updated_at) > _TUI_ORPHAN_LEASE_TTL_S


def _prune_dead(
    entries: list[dict[str, Any]],
    *,
    live_session_ids: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    now = time.time()
    kept: list[dict[str, Any]] = []
    for entry in entries:
        if not _pid_alive(entry.get("pid"), entry.get("process_start_time")):
            continue
        if _entry_is_stale_tui_orphan(
            entry,
            now=now,
            live_session_ids=live_session_ids,
        ):
            continue
        kept.append(entry)
    return kept


@dataclass
class ActiveSessionLease:
    lease_id: str
    session_id: str
    surface: str
    enabled: bool = True
    released: bool = False

    def release(self) -> None:
        if self.released or not self.enabled:
            return
        release_active_session(self)


def try_acquire_active_session(
    *,
    session_id: str,
    surface: str,
    config: Any,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[Optional[ActiveSessionLease], Optional[str]]:
    """Acquire an active-session slot.

    Returns ``(lease, None)`` on success.  When the cap is disabled, the lease is
    a no-op object so callers can unconditionally call ``release()``.
    """
    max_sessions = resolve_max_concurrent_sessions(config)
    lease_id = uuid.uuid4().hex
    if max_sessions is None:
        return ActiveSessionLease(
            lease_id=lease_id,
            session_id=session_id,
            surface=surface,
            enabled=False,
        ), None

    now = time.time()
    entry = {
        "lease_id": lease_id,
        "session_id": str(session_id),
        "surface": str(surface),
        "pid": os.getpid(),
        "process_start_time": _process_start_time(os.getpid()),
        "started_at": now,
        "updated_at": now,
    }
    if metadata:
        entry["metadata"] = {
            str(k): v for k, v in metadata.items() if isinstance(k, str)
        }

    state_path = _state_path()
    with _FileLock(_lock_path()):
        raw_entries = _read_entries(state_path)
        entries = _prune_dead(raw_entries)
        pruned = len(raw_entries) - len(entries)
        if pruned:
            logger.info("Pruned %d stale active session lease(s)", pruned)
        active_count = len(entries)
        if active_count >= max_sessions:
            _write_entries(state_path, entries)
            logger.info(
                "Active session limit reached: active=%d max=%d surface=%s",
                active_count,
                max_sessions,
                surface,
            )
            return None, active_session_limit_message(active_count, max_sessions)
        entries.append(entry)
        _write_entries(state_path, entries)

    return ActiveSessionLease(
        lease_id=lease_id,
        session_id=str(session_id),
        surface=str(surface),
    ), None


def release_active_session(lease: ActiveSessionLease) -> None:
    state_path = _state_path()
    try:
        with _FileLock(_lock_path()):
            entries = _prune_dead(_read_entries(state_path))
            kept = [
                entry
                for entry in entries
                if str(entry.get("lease_id") or "") != lease.lease_id
            ]
            if len(kept) != len(entries):
                _write_entries(state_path, kept)
    finally:
        lease.released = True


def update_active_session(
    lease: ActiveSessionLease,
    *,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """Refresh an active lease and optionally merge metadata.

    TUI/dashboard sessions are owned by a long-lived gateway process, so the
    registry needs a heartbeat plus child-worker metadata. Otherwise a crashed
    or closed UI can leave a live gateway PID behind and pin the profile at its
    active-session limit.
    """
    if lease.released:
        return False
    if not lease.enabled:
        return True

    state_path = _state_path()
    with _FileLock(_lock_path()):
        entries = _prune_dead(_read_entries(state_path))
        updated = False
        for entry in entries:
            if str(entry.get("lease_id") or "") != lease.lease_id:
                continue
            entry["updated_at"] = time.time()
            if metadata:
                current = entry.get("metadata")
                if not isinstance(current, dict):
                    current = {}
                for key, value in metadata.items():
                    if isinstance(key, str):
                        current[str(key)] = value
                entry["metadata"] = current
            updated = True
            break
        if updated:
            _write_entries(state_path, entries)
        return updated


def transfer_active_session(
    lease: ActiveSessionLease,
    *,
    session_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """Move an existing lease to a new session id without dropping the slot."""
    new_session_id = str(session_id or "")
    if not new_session_id:
        return False
    if lease.released:
        return False
    if not lease.enabled:
        lease.session_id = new_session_id
        return True

    state_path = _state_path()
    with _FileLock(_lock_path()):
        entries = _prune_dead(_read_entries(state_path))
        updated = False
        for entry in entries:
            if str(entry.get("lease_id") or "") != lease.lease_id:
                continue
            entry["session_id"] = new_session_id
            entry["updated_at"] = time.time()
            if metadata:
                entry["metadata"] = {
                    str(k): v for k, v in metadata.items() if isinstance(k, str)
                }
            updated = True
            break
        if updated:
            _write_entries(state_path, entries)
            lease.session_id = new_session_id
        return updated


def reconcile_active_sessions(
    *,
    live_session_ids: Optional[set[str]] = None,
) -> int:
    """Prune stale leases and return the number removed.

    ``live_session_ids`` is supplied by the TUI gateway when it knows the
    in-memory session ids. This catches the important Desktop case where the
    gateway process is still alive, but the UI session that claimed the lease
    has already been closed or reaped.
    """
    state_path = _state_path()
    with _FileLock(_lock_path()):
        raw_entries = _read_entries(state_path)
        entries = _prune_dead(raw_entries, live_session_ids=live_session_ids)
        removed = len(raw_entries) - len(entries)
        if removed:
            _write_entries(state_path, entries)
        return removed


def active_session_registry_snapshot() -> list[dict[str, Any]]:
    """Return the pruned active-session registry for diagnostics/tests."""
    state_path = _state_path()
    with _FileLock(_lock_path()):
        entries = _prune_dead(_read_entries(state_path))
        _write_entries(state_path, entries)
        return entries
