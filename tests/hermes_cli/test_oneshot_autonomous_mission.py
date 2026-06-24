from hermes_cli.oneshot import run_oneshot


def test_oneshot_autonomous_mission_returns_runner_report(monkeypatch, capsys):
    class FakeRunner:
        def __init__(self, goal):
            self.goal = goal

        def run(self):
            return "Gate: PASS\n\nMission:\n" + self.goal + "\n"

    monkeypatch.setattr(
        "hermes_cli.autonomy.mission_runner.AutonomousMissionRunner",
        FakeRunner,
    )

    exit_code = run_oneshot("AUTONOMOUS_MISSION: test final report only")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("Gate: PASS")
    assert "AUTONOMOUS_MISSION" in captured.out
