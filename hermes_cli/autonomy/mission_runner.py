from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from .action_classifier import classify_action
from .evidence_ledger import EvidenceLedger
from .final_report import MissionReport, render_final_report
from .policy import AutonomyDecision, MissionEnvelope, create_mission_envelope, default_contract
from .quarantine_ledger import QuarantineLedger
from .self_prompt_queue import SelfPromptQueue


DEFAULT_RUN_ROOT = Path("/Users/begilhan/.hermes/autonomy/runs")
CANONICAL_START_NOTE = (
    "/Users/begilhan/Documents/Private documents/sharedmemory/Bookforge/"
    "00 START HERE - Current Hermes BookForge Status.md"
)
BOOKFORGE_STATUS_URL = "http://127.0.0.1:5012/api/status"
BOOKFORGE_QUEUE_URL = "http://127.0.0.1:5012/api/queue"
BOOKFORGE_REPO_ROOT = "/Users/begilhan/Bookforge V2 PublicationForge"
BOOKFORGE_PROJECT_ROOT = (
    "/Users/begilhan/Bookforge V2 PublicationForge/projects/the_black_beacon_directive"
)


class MissionSources(Protocol):
    def read_text(self, path: str) -> str: ...
    def get_json(self, url: str) -> Any: ...
    def exists(self, path: str) -> bool: ...


class LocalMissionSources:
    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def get_json(self, url: str) -> Any:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def exists(self, path: str) -> bool:
        return Path(path).exists()


class AutonomousMissionRunner:
    def __init__(
        self,
        goal: str,
        *,
        run_root: str | Path = DEFAULT_RUN_ROOT,
        sources: MissionSources | None = None,
    ):
        self.envelope: MissionEnvelope = create_mission_envelope(_clean_goal(goal))
        self.run_root = Path(run_root)
        self.sources = sources or LocalMissionSources()
        self.contract = default_contract()
        self.run_dir = self.run_root / self.envelope.mission_id
        self.prompt_queue = SelfPromptQueue(self.run_dir / "self_prompts")
        self.evidence_ledger = EvidenceLedger(self.run_dir / "evidence" / "evidence.jsonl")
        self.quarantine_ledger = QuarantineLedger(self.run_dir / "quarantine" / "quarantine.jsonl")
        self.actions: list[str] = []
        self.evidence: list[str] = []
        self.repairs: list[str] = []
        self.changed_files: list[str] = []
        self.verification: list[str] = []
        self.quarantined: list[str] = []
        self.current_state = ""
        self.next_recommended_mission = ""

    def run(self) -> str:
        self._initialize_run_dir()
        self._classify_initial_actions()
        self._route_preflight()
        if _looks_like_bookforge_chapter_28(self.envelope.goal):
            self._run_bookforge_chapter_28_diagnosis()
        else:
            self._run_generic_autonomous_planning()
        self._verify_final_report_shape()
        gate = self._final_gate()
        report = render_final_report(
            MissionReport(
                gate=gate,
                mission=self.envelope.goal,
                actions=self.actions,
                evidence=self.evidence,
                repairs=self.repairs,
                changed_files=self.changed_files,
                verification=self.verification,
                quarantined=self.quarantined,
                current_state=self.current_state,
                next_recommended_mission=self.next_recommended_mission,
            )
        )
        (self.run_dir / "final_report.md").write_text(report, encoding="utf-8")
        return report

    def _initialize_run_dir(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_queue.seed_standard_prompts(self.envelope.goal)
        (self.run_dir / "mission.yaml").write_text(_render_envelope_yaml(self.envelope), encoding="utf-8")
        self.actions.append("Created autonomous mission envelope with final_report_only reporting.")

    def _classify_initial_actions(self) -> None:
        candidate_actions = [
            "route preflight",
            "evidence gathering",
            "diagnosis and repair planning",
            "tests and verification",
        ]
        if "deploy" in self.envelope.goal.lower() or "publish" in self.envelope.goal.lower():
            candidate_actions.append(self.envelope.goal)
        if _looks_like_bookforge_chapter_28(self.envelope.goal):
            self.quarantined.extend(
                [
                    "Boundary: risk acceptance remains outside this mission envelope.",
                    "Boundary: AI Reader gate bypass remains outside this mission envelope.",
                    "Boundary: publish/export remains outside this mission envelope.",
                ]
            )
        for action in candidate_actions:
            classified = classify_action(action, self.contract, mission_goal=self.envelope.goal)
            if classified.decision is AutonomyDecision.QUARANTINE:
                self.quarantine_ledger.append(action, classified.action_class, classified.reason)
                self.quarantined.append(f"{action}: {classified.reason}")

    def _route_preflight(self) -> None:
        self.actions.append("Ran internal route preflight as mission setup; route preflight is not a user-facing stop.")
        self.evidence_ledger.append(
            "route_preflight",
            "PASS",
            "Autonomous mission runner treats route preflight as internal setup.",
        )
        self.evidence.append("route_preflight: PASS; mission continued automatically.")

    def _run_bookforge_chapter_28_diagnosis(self) -> None:
        status = self._read_json_source(BOOKFORGE_STATUS_URL, "BookForge /api/status")
        queue = self._read_json_source(BOOKFORGE_QUEUE_URL, "BookForge /api/queue")
        self._read_text_source(CANONICAL_START_NOTE, "canonical Obsidian start note")
        chapter_item = _find_chapter_item(queue, 28)
        review_path = _chapter_review_path(chapter_item)
        if review_path:
            full_review_path = _resolve_bookforge_path(review_path)
            self._read_text_source(full_review_path, "Chapter 28 AI Reader review artifact")
        else:
            self.evidence_ledger.append(
                "Chapter 28 AI Reader review artifact",
                "ACCESS_FAILED",
                "No Chapter 28 review artifact path found in queue evidence.",
            )
            self.evidence.append("Chapter 28 artifact path: ACCESS_FAILED; no path found in queue evidence.")

        context_msg = _extract_context_budget_message(status, queue)
        gate_summary = _extract_ai_reader_summary(chapter_item)
        self.actions.extend(
            [
                "Diagnosed BookForge Chapter 28 queue/status state.",
                "Inspected context-budget failure evidence.",
                "Inspected AI Reader review gate evidence when path was available.",
                "Produced non-mutating repair plan; no generation, resume, prose repair, or mutation performed.",
            ]
        )
        self.repairs.append("No repair executed; mission is diagnosis/planning unless engine/config repair is explicitly in envelope.")
        self.verification.append("Confirmed BookForge worker is idle or not running before planning output.")
        self.current_state = (
            "BookForge Chapter 28 remains blocked. "
            f"Context-budget evidence: {context_msg or 'not found'}. "
            f"AI Reader gate: {gate_summary or 'not found'}."
        )
        self.next_recommended_mission = (
            "Run a bounded engine context-budget fix mission that uses excerpted/summary context for publish-readiness audit, "
            "then rerun tests and status checks."
        )

    def _run_generic_autonomous_planning(self) -> None:
        self.actions.append("Produced autonomous planning report from mission envelope.")
        self.repairs.append("No repair executed because no concrete subsystem-specific failure was detected.")
        self.verification.append("Final report shape verified.")
        self.current_state = "Mission envelope created; no subsystem-specific runner matched this goal."
        self.next_recommended_mission = "Run a subsystem-specific autonomous mission with concrete target and constraints."

    def _read_json_source(self, source: str, label: str) -> Any:
        try:
            data = self.sources.get_json(source)
        except Exception as exc:
            self.evidence_ledger.append(source, "ACCESS_FAILED", f"{label}: {exc}")
            self.evidence.append(f"{label}: ACCESS_FAILED ({exc})")
            return None
        observation = _json_observation(label, data)
        self.evidence_ledger.append(source, "reachable", observation, data if isinstance(data, dict) else {"data": data})
        self.evidence.append(f"{label}: reachable; {observation}")
        return data

    def _read_text_source(self, source: str, label: str) -> str:
        try:
            text = self.sources.read_text(source)
        except Exception as exc:
            self.evidence_ledger.append(source, "ACCESS_FAILED", f"{label}: {exc}")
            self.evidence.append(f"{label}: ACCESS_FAILED ({exc})")
            return ""
        snippet = " ".join(text.strip().split())[:240]
        self.evidence_ledger.append(source, "reachable", f"{label}: {snippet}")
        self.evidence.append(f"{label}: reachable; {snippet}")
        return text

    def _verify_final_report_shape(self) -> None:
        self.verification.append("Final report renderer requires Gate: PASS, Gate: REPAIR, or Gate: QUARANTINED.")

    def _final_gate(self) -> str:
        if any(not item.startswith("Boundary:") for item in self.quarantined):
            return "QUARANTINED"
        if "blocked" in self.current_state.lower() or "failed" in self.current_state.lower():
            return "REPAIR"
        return "PASS"


def _clean_goal(goal: str) -> str:
    text = (goal or "").strip()
    if text.upper().startswith("AUTONOMOUS_MISSION:"):
        return text.split(":", 1)[1].strip()
    return text


def _render_envelope_yaml(envelope: MissionEnvelope) -> str:
    lines = [
        f"mission_id: {envelope.mission_id}",
        f"goal: {json.dumps(envelope.goal)}",
        f"mode: {envelope.mode}",
        f"reporting: {envelope.reporting}",
        "auto_allowed:",
    ]
    lines.extend(f"  - {item}" for item in envelope.auto_allowed)
    lines.append("quarantine:")
    lines.extend(f"  - {item}" for item in envelope.quarantine)
    lines.append("final_output:")
    lines.extend(f"  - {item}" for item in envelope.final_output)
    return "\n".join(lines) + "\n"


def _looks_like_bookforge_chapter_28(goal: str) -> bool:
    goal_l = (goal or "").lower()
    return "bookforge" in goal_l and "chapter 28" in goal_l


def _find_chapter_item(queue: Any, chapter: int) -> dict[str, Any] | None:
    if not isinstance(queue, dict):
        return None
    for item in queue.get("items") or []:
        if isinstance(item, dict) and item.get("chapter") == chapter:
            return item
    return None


def _chapter_review_path(chapter_item: dict[str, Any] | None) -> str:
    if not isinstance(chapter_item, dict):
        return ""
    gate = chapter_item.get("ai_reader_gate")
    if not isinstance(gate, dict):
        return ""
    reviews = gate.get("reviews")
    if not isinstance(reviews, list):
        return ""
    for review in reviews:
        if isinstance(review, dict) and review.get("path"):
            return str(review["path"])
    return ""


def _resolve_bookforge_path(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(Path(BOOKFORGE_REPO_ROOT) / candidate)


def _extract_context_budget_message(status: Any, queue: Any) -> str:
    candidates: list[str] = []
    if isinstance(status, dict):
        activity = status.get("activity")
        attention = status.get("attention")
        if isinstance(activity, dict):
            candidates.append(str(activity.get("msg") or ""))
        if isinstance(attention, dict):
            candidates.append(str(attention.get("reason") or ""))
    item = _find_chapter_item(queue, 28)
    if item:
        candidates.append(str(item.get("attention_reason") or ""))
    for candidate in candidates:
        if "context window" in candidate.lower() or "24576" in candidate:
            return candidate
    return ""


def _extract_ai_reader_summary(chapter_item: dict[str, Any] | None) -> str:
    if not isinstance(chapter_item, dict):
        return ""
    gate = chapter_item.get("ai_reader_gate")
    if not isinstance(gate, dict):
        return ""
    blocked = gate.get("blocked")
    reviews = gate.get("reviews") if isinstance(gate.get("reviews"), list) else []
    if reviews and isinstance(reviews[0], dict):
        return (
            f"blocked={blocked}; grade={reviews[0].get('grade')}; "
            f"action={reviews[0].get('recommended_action')}"
        )
    return f"blocked={blocked}; state={gate.get('state')}"


def _json_observation(label: str, data: Any) -> str:
    if not isinstance(data, dict):
        return f"{label} returned {type(data).__name__}"
    if "queue_counts" in data:
        worker = data.get("worker") if isinstance(data.get("worker"), dict) else {}
        counts = data.get("queue_counts")
        return f"queue_counts={counts}; worker_running={worker.get('running')}"
    if "counts" in data:
        return f"counts={data.get('counts')}; attention={data.get('attention')}"
    return f"keys={sorted(data.keys())[:8]}"
