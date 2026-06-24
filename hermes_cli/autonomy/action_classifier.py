from __future__ import annotations

from dataclasses import dataclass
import re

from .policy import AutonomyContract, AutonomyDecision
from .mission_text import requested_action_text


@dataclass(frozen=True)
class ClassifiedAction:
    action: str
    action_class: str
    decision: AutonomyDecision
    reason: str


def classify_action(
    action: str,
    contract: AutonomyContract,
    *,
    mission_goal: str = "",
) -> ClassifiedAction:
    text = requested_action_text(action or "")
    lower = text.lower()
    goal_l = requested_action_text(mission_goal or "").lower()

    if _is_external_or_irreversible(lower):
        return ClassifiedAction(
            text,
            "A7",
            AutonomyDecision.QUARANTINE,
            "external, irreversible, financial, account, deploy, publish, secret, destructive, or risk action",
        )

    if "chapter 15" in lower and "chapter 15" not in goal_l:
        return ClassifiedAction(
            text,
            "A7",
            AutonomyDecision.QUARANTINE,
            "chapter 15 recovery is outside the mission envelope",
        )

    if _looks_like_broad_manuscript_rewrite(lower) and not _mission_explicitly_allows_rewrite(goal_l):
        return ClassifiedAction(
            text,
            "A7",
            AutonomyDecision.QUARANTINE,
            "broad manuscript rewrite is outside the mission envelope",
        )

    if any(word in lower for word in ("bookforge bounded repair", "bounded repair", "re-review")):
        if "bookforge repair" in goal_l or "production run" in goal_l or "bounded repair" in goal_l:
            return ClassifiedAction(text, "A6", AutonomyDecision.AUTO, "BookForge bounded repair is in mission")
        return ClassifiedAction(
            text,
            "A6",
            AutonomyDecision.QUARANTINE,
            "BookForge bounded repair requires explicit mission inclusion",
        )

    if any(word in lower for word in ("unload", "restart", "health check", "retry model", "omlx")):
        return ClassifiedAction(text, "A5", AutonomyDecision.AUTO, "safe local runtime repair")

    if any(word in lower for word in ("patch", "edit", "fix code", "config", "with backup")):
        return ClassifiedAction(text, "A4", AutonomyDecision.AUTO, "bounded local code/config change with backup")

    if any(word in lower for word in ("test", "pytest", "verify", "smoke", "validation")):
        return ClassifiedAction(text, "A3", AutonomyDecision.AUTO, "local tests or verification")

    if any(word in lower for word in ("diagnose", "plan", "repair plan", "planning")):
        return ClassifiedAction(text, "A2", AutonomyDecision.AUTO, "planning or diagnosis")

    if any(word in lower for word in ("evidence", "packet", "status reconstruction", "route preflight")):
        return ClassifiedAction(text, "A1", AutonomyDecision.AUTO, "evidence or packet work")

    return ClassifiedAction(text, "A0", AutonomyDecision.AUTO, "read-only inspection")


def _is_external_or_irreversible(text: str) -> bool:
    keywords = (
        "external posting",
        "post to",
        "deploy",
        "deployment",
        "publish/export",
        "publish when done",
        "publish to",
        "publish the",
        "publish book",
        "publish manuscript",
        "export for publication",
        "payment",
        "account action",
        "secret",
        "credential",
        "destructive delete",
        "delete model",
        "rm -rf",
        "risk acceptance",
        "accept risk",
        "bypass gate",
        "bypass ai reader",
    )
    if any(k in text for k in keywords):
        return True
    return bool(re.search(r"\bexport\b", text) and not re.search(r"\b(import|export json|exported report)\b", text))


def _looks_like_broad_manuscript_rewrite(text: str) -> bool:
    return "rewrite" in text and any(k in text for k in ("chapter", "book", "manuscript", "prose"))


def _mission_explicitly_allows_rewrite(goal: str) -> bool:
    return "rewrite" in goal and any(k in goal for k in ("chapter", "book", "manuscript", "prose"))
