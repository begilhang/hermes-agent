from types import SimpleNamespace


def test_run_conversation_autonomous_mission_uses_runner_without_api(monkeypatch):
    from agent.conversation_loop import run_conversation

    class FakeRunner:
        def __init__(self, goal):
            self.goal = goal

        def run(self):
            return "Gate: PASS\n\nMission:\n" + self.goal + "\n"

    monkeypatch.setattr(
        "hermes_cli.autonomy.mission_runner.AutonomousMissionRunner",
        FakeRunner,
    )

    agent = SimpleNamespace(
        platform="tui",
        model="gpt-5.5",
        provider="openai-codex",
        base_url="https://chatgpt.com/backend-api/codex",
    )

    result = run_conversation(
        agent,
        "AUTONOMOUS_MISSION: Diagnose BookForge Chapter 28. Return final report only.",
    )

    assert result["completed"] is True
    assert result["api_calls"] == 0
    assert result["exit_reason"] == "autonomous_mission"
    assert result["final_response"].startswith("Gate: PASS")
    assert "AUTONOMOUS_MISSION" in result["final_response"]

