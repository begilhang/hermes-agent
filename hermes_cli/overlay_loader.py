"""Update-safe overlay loader for local Hermes customizations.

Hermes core should keep update-sensitive custom behavior behind tiny hook
points. The actual behavior lives outside this repo under
``~/.hermes/overlays/hermes_architecture_v1`` so upstream updates can be
audited and re-applied without losing local operating policy.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType


DEFAULT_OVERLAY_SRC = (
    Path.home()
    / ".hermes"
    / "overlays"
    / "hermes_architecture_v1"
    / "src"
)


def overlay_src_path() -> Path:
    configured = os.getenv("HERMES_ARCHITECTURE_V1_OVERLAY_SRC", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_OVERLAY_SRC


def load_architecture_overlay(module_name: str) -> ModuleType:
    """Import ``hermes_architecture_v1.<module_name>`` from the overlay.

    Raises ImportError when the overlay is not installed; callers should keep
    a small local fallback only where startup safety requires it.
    """

    src = overlay_src_path()
    if not src.exists():
        raise ImportError(f"Hermes Architecture v1 overlay src missing: {src}")
    src_s = str(src)
    if src_s not in sys.path:
        sys.path.insert(0, src_s)
    module = f"hermes_architecture_v1.{module_name}".rstrip(".")
    return importlib.import_module(module)
