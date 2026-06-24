from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AutonomyDecision(str, Enum):
    AUTO = "auto"
    QUARANTINE = "quarantine"


DEFAULT_AUTO_ALLOWED = [
    "read_only_inspection",
    "evidence_gathering",
    "status_reconstruction",
    "planning",
    "local_tests",
    "smoke_checks",
    "packet_repair",
    "route_repair",
    "local_config_diagnosis",
    "bounded_code_fixes_with_backup",
    "verifier_reruns",
    "local_runtime_health_checks",
    "safe_model_unload_retry",
    "obsidian_status_updates",
]

DEFAULT_QUARANTINE = [
    "external_posting",
    "deployment",
    "publish_export",
    "payment_account_actions",
    "secrets_changes",
    "destructive_deletes",
    "risk_acceptance",
    "chapter_15_recovery_unless_explicitly_included",
    "broad_manuscript_rewrite_unless_explicitly_included",
]

DEFAULT_FINAL_OUTPUT = ["PASS", "REPAIR", "QUARANTINED"]


@dataclass(frozen=True)
class AutonomyContract:
    auto_allowed: list[str]
    quarantine: list[str]
    final_output: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "auto_allowed": list(self.auto_allowed),
            "quarantine": list(self.quarantine),
            "final_output": list(self.final_output),
        }


@dataclass(frozen=True)
class MissionEnvelope:
    mission_id: str
    goal: str
    mode: str
    reporting: str
    auto_allowed: list[str]
    quarantine: list[str]
    final_output: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "goal": self.goal,
            "mode": self.mode,
            "reporting": self.reporting,
            "auto_allowed": list(self.auto_allowed),
            "quarantine": list(self.quarantine),
            "final_output": list(self.final_output),
        }


def default_contract() -> AutonomyContract:
    return AutonomyContract(
        auto_allowed=list(DEFAULT_AUTO_ALLOWED),
        quarantine=list(DEFAULT_QUARANTINE),
        final_output=list(DEFAULT_FINAL_OUTPUT),
    )


def create_mission_envelope(goal: str, *, mission_id: str | None = None) -> MissionEnvelope:
    contract = default_contract()
    clean_goal = (goal or "").strip()
    generated_id = mission_id or _mission_id_from_goal(clean_goal)
    return MissionEnvelope(
        mission_id=generated_id,
        goal=clean_goal,
        mode="autonomous",
        reporting="final_only",
        auto_allowed=contract.auto_allowed,
        quarantine=contract.quarantine,
        final_output=contract.final_output,
    )


def _mission_id_from_goal(goal: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", goal.lower()).strip("-")[:48]
    return f"mission-{slug or 'autonomous'}-{uuid.uuid4().hex[:8]}"
