from __future__ import annotations

import sys
from pathlib import Path


def test_overlay_loader_imports_configured_module(monkeypatch, tmp_path):
    package = tmp_path / "hermes_architecture_v1"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "example.py").write_text("VALUE = 42\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_ARCHITECTURE_V1_OVERLAY_SRC", str(tmp_path))
    sys.modules.pop("hermes_architecture_v1.example", None)

    from hermes_cli.overlay_loader import load_architecture_overlay, overlay_src_path

    assert overlay_src_path() == Path(tmp_path)
    module = load_architecture_overlay("example")
    assert module.VALUE == 42
