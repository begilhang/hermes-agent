from __future__ import annotations

from pathlib import Path


class SelfPromptQueue:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return path

    def seed_standard_prompts(self, goal: str) -> None:
        prompts = {
            "001_route_preflight.md": "Run internal route preflight, then continue the mission.",
            "002_evidence_gathering.md": "Gather all allowed evidence sources. Do not ask the user.",
            "003_diagnosis.md": "Diagnose from gathered evidence.",
            "004_repair_plan.md": "Produce repair plan. Do not execute quarantined actions.",
            "005_patch_if_allowed.md": "Patch only if inside the mission envelope and backup exists.",
            "006_verify.md": "Run verification and collect evidence.",
            "007_repair_failed_checks.md": "Repair failed checks up to configured attempts.",
            "008_final_report.md": "Render final report only.",
        }
        for name, instruction in prompts.items():
            self.write(name, f"Mission: {goal}\n\n{instruction}")

    def write_repair_attempt(self, stage: str, attempt: int, content: str) -> Path:
        safe_stage = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stage)
        return self.write(f"{safe_stage}_REPAIR_ATTEMPT_{attempt}.md", content)
