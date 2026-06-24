"""Small bridge for user-owned Hermes overlays.

Core Hermes should only import stable hook entrypoints from this module.
Custom behavior lives outside the repo under ~/.hermes/overlays so upstream
updates are easier to audit and reapply.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType


DEFAULT_OVERLAY_SRC = (
    Path.home() / ".hermes" / "overlays" / "hermes_architecture_v1" / "src"
)


def overlay_src_path() -> Path:
    configured = os.getenv("HERMES_ARCHITECTURE_V1_OVERLAY_SRC", "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_OVERLAY_SRC


def load_architecture_overlay(module_name: str) -> ModuleType:
    """Load a Hermes Architecture v1 overlay module.

    Raises ImportError when the overlay is unavailable. Callers should treat
    that as "no overlay handled this request" except for explicit deterministic
    modes such as ROUTE_PREFLIGHT_ONLY.
    """

    src = overlay_src_path()
    if not src.exists():
        raise ImportError(f"Hermes Architecture v1 overlay not found: {src}")
    src_s = str(src)
    if src_s not in sys.path:
        sys.path.insert(0, src_s)
    _ensure_overlay_package_from(src)
    dotted = f"hermes_architecture_v1.{module_name.strip('.')}"
    return importlib.import_module(dotted)


def _ensure_overlay_package_from(src: Path) -> None:
    pkg = sys.modules.get("hermes_architecture_v1")
    if pkg is None:
        return
    pkg_file = getattr(pkg, "__file__", None)
    if not pkg_file:
        return
    try:
        Path(pkg_file).resolve().relative_to(src.resolve())
        return
    except Exception:
        pass
    for name in list(sys.modules):
        if name == "hermes_architecture_v1" or name.startswith("hermes_architecture_v1."):
            sys.modules.pop(name, None)
