import json

from agent.local_worker_guard import session_search_context_block
import model_tools


def _enable_guard(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {
            "local_worker_enforcement": {
                "enabled": True,
                "max_parent_read_lines": 120,
                "max_parent_read_bytes": 8192,
                "ceo_context_preservation": {
                    "enabled": True,
                    "max_parent_search_results": 20,
                    "max_parent_session_search_chars": 12000,
                    "max_parent_session_search_limit": 3,
                    "max_parent_session_search_window": 5,
                },
            }
        },
    )


def test_parent_broad_read_is_blocked_when_local_worker_enforcement_enabled(tmp_path, monkeypatch):
    _enable_guard(monkeypatch)
    source = tmp_path / "large-note.md"
    source.write_text("\n".join(f"line {i}" for i in range(200)), encoding="utf-8")

    result = json.loads(
        model_tools.handle_function_call(
            "read_file",
            {"path": str(source), "limit": 500},
            task_id="parent-session",
        )
    )

    assert "CHEAP_LOCAL_WORKER_REQUIRED" in result["error"]
    assert "delegate_task" in result["error"]


def test_parent_narrow_read_is_allowed_when_local_worker_enforcement_enabled(tmp_path, monkeypatch):
    _enable_guard(monkeypatch)
    source = tmp_path / "large-note.md"
    source.write_text("\n".join(f"line {i}" for i in range(200)), encoding="utf-8")

    result = json.loads(
        model_tools.handle_function_call(
            "read_file",
            {"path": str(source), "limit": 20},
            task_id="parent-session",
        )
    )

    assert not result.get("error")
    assert "line 0" in result.get("content", "")


def test_subagent_broad_read_is_allowed_when_parent_guard_is_enabled(tmp_path, monkeypatch):
    _enable_guard(monkeypatch)
    source = tmp_path / "large-note.md"
    source.write_text("\n".join(f"line {i}" for i in range(200)), encoding="utf-8")

    result = json.loads(
        model_tools.handle_function_call(
            "read_file",
            {"path": str(source), "limit": 500},
            task_id="sa-0-test1234",
        )
    )

    assert not result.get("error")
    assert "line 0" in result.get("content", "")


def test_parent_broad_terminal_discovery_is_blocked(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "terminal",
            {"command": "printf should-not-run # rg -n TODO ."},
            task_id="parent-session",
        )
    )

    assert "CHEAP_LOCAL_WORKER_REQUIRED" in result["error"]
    assert "delegate_task" in result["error"]


def test_parent_narrow_terminal_health_check_is_allowed(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "terminal",
            {"command": "printf OK"},
            task_id="parent-session",
        )
    )

    assert not result.get("error")
    assert result.get("output", "").strip() == "OK"


def test_subagent_broad_terminal_discovery_is_allowed(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "terminal",
            {"command": "printf 'subagent can inspect' # rg -n TODO ."},
            task_id="sa-0-test1234",
        )
    )

    assert not result.get("error")
    assert "subagent can inspect" in result.get("output", "")


def test_parent_broad_search_files_is_blocked(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "search_files",
            {"pattern": "TODO", "path": ".", "limit": 50, "output_mode": "content"},
            task_id="parent-session",
        )
    )

    assert "CHEAP_LOCAL_WORKER_REQUIRED" in result["error"]
    assert "delegate_task" in result["error"]


def test_parent_broad_execute_code_discovery_is_blocked(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "execute_code",
            {
                "code": (
                    "import subprocess\n"
                    "subprocess.run(['grep', '-rn', '61.11GB', '/Users/begilhan'], "
                    "capture_output=True, text=True)\n"
                )
            },
            task_id="parent-session",
        )
    )

    assert "CHEAP_LOCAL_WORKER_REQUIRED" in result["error"]
    assert "delegate_task" in result["error"]


def test_subagent_broad_execute_code_discovery_is_allowed(monkeypatch):
    _enable_guard(monkeypatch)

    result = json.loads(
        model_tools.handle_function_call(
            "execute_code",
            {
                "code": (
                    "import subprocess\n"
                    "result = subprocess.run(['printf', 'worker OK'], "
                    "capture_output=True, text=True)\n"
                    "print(result.stdout)\n"
                )
            },
            task_id="sa-0-test1234",
        )
    )

    assert not result.get("error")
    assert "worker OK" in result.get("output", "")


def test_parent_session_search_full_read_is_blocked(monkeypatch):
    _enable_guard(monkeypatch)

    blocked = session_search_context_block(
        {"session_id": "20260622_200413_5783bd"},
        task_id="parent-session",
    )

    assert blocked is not None
    result = json.loads(blocked)
    assert result["code"] == "CHEAP_LOCAL_WORKER_REQUIRED"
    assert "Full-session reads" in result["error"]
    assert "delegate_task" in result["next_action"]


def test_parent_large_session_search_output_is_blocked(monkeypatch):
    _enable_guard(monkeypatch)

    blocked = session_search_context_block(
        {"query": "bookforge", "limit": 3},
        task_id="parent-session",
        result="x" * 13000,
    )

    assert blocked is not None
    result = json.loads(blocked)
    assert result["code"] == "CHEAP_LOCAL_WORKER_REQUIRED"
    assert "session_search returned 13000 characters" in result["error"]


def test_subagent_large_session_search_output_is_allowed(monkeypatch):
    _enable_guard(monkeypatch)

    blocked = session_search_context_block(
        {"query": "bookforge", "limit": 3},
        task_id="sa-0-test1234",
        result="x" * 13000,
    )

    assert blocked is None
