import json
from pathlib import Path

from hermes_cli.autonomy.mission_runner import AutonomousMissionRunner


class FakeSources:
    def __init__(self):
        self.read_paths = []
        self.status = {
            "activity": {
                "phase": "failed",
                "msg": "Context window would be exceeded: input=90325 + output=8000 + safety=512 = 98837 >= 24576",
            },
            "worker": {"running": False},
            "queue_counts": {"failed": 1, "pending": 0, "running": 0},
            "generation_preflight": {"allowed": False, "code": "no_runnable_queue_item"},
        }
        self.queue = {
            "counts": {"failed": 1, "pending": 0, "running": 0},
            "items": [
                {
                    "chapter": 28,
                    "attention_state": "failed",
                    "attention_reason": "Context window would be exceeded: input=90325 + output=8000 + safety=512 = 98837 >= 24576",
                    "ai_reader_gate": {
                        "blocked": True,
                        "state": "blocked",
                        "reviews": [
                            {
                                "grade": "C",
                                "recommended_action": "NEEDS SURGICAL REPAIR",
                                "path": "projects/the_black_beacon_directive/reports/chapter_28_ai_reader_review.md",
                            }
                        ],
                    },
                }
            ],
        }

    def read_text(self, path: str) -> str:
        self.read_paths.append(path)
        if "START HERE" in path:
            return "BookForge Chapter 28 read-only diagnosis and context-budget repair planning is next."
        if "chapter_28_ai_reader_review" in path:
            return "grade C NEEDS SURGICAL REPAIR decisive choice visible cost changed order"
        return ""

    def get_json(self, url: str):
        if url.endswith("/api/status"):
            return self.status
        if url.endswith("/api/queue"):
            return self.queue
        raise OSError(url)

    def exists(self, path: str) -> bool:
        return True


def test_bookforge_chapter_28_autonomous_mission_returns_final_report_only(tmp_path):
    sources = FakeSources()
    runner = AutonomousMissionRunner(
        "AUTONOMOUS_MISSION: Diagnose BookForge Chapter 28 context-budget failure. No generation, no mutation. Return final report only.",
        run_root=tmp_path,
        sources=sources,
    )

    report = runner.run()

    assert report.startswith("Gate: REPAIR")
    assert "Context window would be exceeded" in report
    assert "24576" in report
    assert "AI Reader" in report
    assert "Risk acceptance" in report or "risk acceptance" in report
    assert "Approve" not in report
    assert "Do you want" not in report
    assert not any("projects/projects" in path for path in sources.read_paths)
    assert (tmp_path / runner.envelope.mission_id / "mission.yaml").exists()
    assert (tmp_path / runner.envelope.mission_id / "final_report.md").read_text()


def test_forbidden_actions_are_quarantined_not_executed(tmp_path):
    runner = AutonomousMissionRunner(
        "AUTONOMOUS_MISSION: Diagnose BookForge and deploy/publish when done.",
        run_root=tmp_path,
        sources=FakeSources(),
    )

    report = runner.run()

    assert report.startswith("Gate: QUARANTINED")
    assert "deployment" in report.lower() or "deploy" in report.lower()
    quarantine_files = list((tmp_path / runner.envelope.mission_id / "quarantine").glob("*.jsonl"))
    assert quarantine_files
    entries = [json.loads(line) for line in quarantine_files[0].read_text().splitlines()]
    assert any("deploy" in entry["action"].lower() for entry in entries)


def test_self_prompts_and_evidence_ledgers_are_written(tmp_path):
    runner = AutonomousMissionRunner(
        "AUTONOMOUS_MISSION: Diagnose BookForge Chapter 28 context-budget failure.",
        run_root=tmp_path,
        sources=FakeSources(),
    )

    runner.run()
    run_dir = tmp_path / runner.envelope.mission_id

    assert (run_dir / "self_prompts" / "001_route_preflight.md").exists()
    assert (run_dir / "self_prompts" / "008_final_report.md").exists()
    assert (run_dir / "evidence" / "evidence.jsonl").exists()
