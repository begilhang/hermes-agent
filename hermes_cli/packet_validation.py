"""Validation gates for delegated orchestration packets.

These checks are intentionally deterministic.  A Brain CEO should not consume
delegated worker prose merely because it is non-empty; packet-shaped tasks must
produce packet-shaped evidence or fail closed before the parent reasons over it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


FORBIDDEN_PACKET_PHRASES = (
    "start generation",
    "continue generation",
    "accept risk",
    "bypass the ai reader",
    "bypass ai reader",
)

FORBIDDEN_PACKET_PATTERNS = (
    re.compile(r"\b(resume|start|continue)\b.{0,80}\bbookforge\b.{0,80}\bgeneration\b", re.I),
    re.compile(r"\bbookforge\b.{0,80}\b(resume|start|continue)\b.{0,80}\bgeneration\b", re.I),
)

PENDING_EVIDENCE_PATTERNS = (
    re.compile(r"\bevidence\b.{0,80}\bpending\b", re.I | re.S),
    re.compile(r"\bto be (read|polled|checked|inspected)\b", re.I),
    re.compile(r"\b(files|artifacts) inspected:\s*none\b", re.I),
    re.compile(r"\bverification run:\s*none\b", re.I),
    re.compile(r"\bif (?:paths?|sources?|artifacts?)\b.{0,80}\b(discoverable|available|found)\b", re.I),
)

TOOL_NARRATION_PATTERNS = (
    re.compile(r"\bI (will|would|am going to|need to) (run|read|inspect|check)\b", re.I),
    re.compile(r"\bLet me (run|read|inspect|check)\b", re.I),
    re.compile(r"\bRan command\b", re.I),
)

CONCRETE_EVIDENCE_PATTERNS = (
    re.compile(r"\bACCESS_FAILED\b", re.I),
    re.compile(r"\b(reachable|unreachable)\b", re.I),
    re.compile(r"\b(?:response|status|queue|packet|preflight)\b.{0,40}\b(?:reports|says|shows|returned|contains)\b", re.I),
    re.compile(r"\b(?:status|queue|packet|preflight|worker|gate)\s*[:=]\s*\S+", re.I),
    re.compile(r"\bchapter\s+\d+\b.{0,80}\b(?:failed|blocked|passed|pending|running|stopped|completed)\b", re.I),
    re.compile(r"\b(?:worker|queue|preflight|gate)\b.{0,80}\b(?:running|idle|failed|blocked|passed|pending|stopped|completed)\b", re.I),
    re.compile(r"\b(?:artifact|file|path)\b.{0,80}\b(?:/Users/|missing|found|exists|not found|ACCESS_FAILED)\b", re.I),
)


@dataclass(frozen=True)
class PacketValidationResult:
    valid: bool
    code: str
    reason: str = ""


def requires_ceo_decision_packet(goal: str) -> bool:
    text = (goal or "").lower()
    return (
        "ceo_decision_packet" in text
        or "ceo decision packet" in text
        or "compact ceo packet" in text
    )


def validate_route_preflight_packet(text: str) -> PacketValidationResult:
    try:
        packet = json.loads(text or "")
    except Exception as exc:
        return PacketValidationResult(False, "ROUTE_PACKET_INVALID", f"invalid JSON: {exc}")
    if not isinstance(packet, dict):
        return PacketValidationResult(False, "ROUTE_PACKET_INVALID", "route packet is not an object")
    gate = packet.get("route_gate")
    if gate not in {"ROUTE_PASS", "ROUTE_FAIL", "ROUTE_UNVERIFIED"}:
        return PacketValidationResult(False, "ROUTE_PACKET_INVALID", "missing/invalid route_gate")
    if gate == "ROUTE_PASS":
        missing = [
            key
            for key in (
                "effective_profile",
                "effective_model",
                "effective_provider",
                "effective_base_url",
                "fallback_chain",
                "surface",
            )
            if not packet.get(key)
        ]
        if missing:
            return PacketValidationResult(
                False,
                "ROUTE_PACKET_INVALID",
                f"ROUTE_PASS missing required field(s): {', '.join(missing)}",
            )
    if packet.get("secrets_printed") is not False:
        return PacketValidationResult(False, "ROUTE_PACKET_INVALID", "secrets_printed must be false")
    if packet.get("forbidden_fallback_detected") not in {True, False}:
        return PacketValidationResult(
            False,
            "ROUTE_PACKET_INVALID",
            "forbidden_fallback_detected must be boolean",
        )
    return PacketValidationResult(True, "ROUTE_PACKET_VALID")


def validate_ceo_decision_packet(text: str, *, forbidden_actions: bool = True) -> PacketValidationResult:
    body = (text or "").strip()
    if not body:
        return PacketValidationResult(False, "PACKET_INVALID", "empty packet")
    if not body.startswith("CEO_DECISION_PACKET"):
        return PacketValidationResult(False, "PACKET_INVALID", "packet must start with CEO_DECISION_PACKET")
    lower = body.lower()
    required_markers = (
        "current",
        "evidence",
        "risk",
        "recommend",
        "decision",
    )
    missing = [marker for marker in required_markers if marker not in lower]
    if missing:
        return PacketValidationResult(
            False,
            "PACKET_INVALID",
            f"missing required packet marker(s): {', '.join(missing)}",
        )
    if not re.search(r"(/Users/|http://127\.0\.0\.1|`[^`]+`|\[[^\]]+\]\([^)]+\))", body):
        return PacketValidationResult(False, "PACKET_INVALID", "packet lacks concrete evidence path/endpoint/reference")
    if any(pattern.search(body) for pattern in TOOL_NARRATION_PATTERNS):
        return PacketValidationResult(False, "PACKET_INVALID", "packet narrates planned tool work instead of evidence")
    if any(pattern.search(body) for pattern in PENDING_EVIDENCE_PATTERNS):
        return PacketValidationResult(False, "PACKET_INVALID", "packet lists pending evidence instead of verified evidence")
    if forbidden_actions:
        for pattern in FORBIDDEN_PACKET_PATTERNS:
            if pattern.search(body):
                return PacketValidationResult(
                    False,
                    "PACKET_INVALID",
                    "forbidden BookForge generation action detected",
                )
        for phrase in FORBIDDEN_PACKET_PHRASES:
            if phrase in lower:
                return PacketValidationResult(
                    False,
                    "PACKET_INVALID",
                    f"forbidden action recommendation detected: {phrase}",
                )
    if not any(pattern.search(body) for pattern in CONCRETE_EVIDENCE_PATTERNS):
        return PacketValidationResult(
            False,
            "PACKET_INVALID",
            "packet lacks concrete evidence observation",
        )
    return PacketValidationResult(True, "PACKET_VALID")


def validate_delegated_output(goal: str, summary: str) -> PacketValidationResult:
    goal_l = (goal or "").lower()
    if "route_preflight_only" in goal_l or "route preflight" in goal_l or "route-preflight" in goal_l:
        return validate_route_preflight_packet(summary)
    if requires_ceo_decision_packet(goal):
        return validate_ceo_decision_packet(summary)
    return PacketValidationResult(True, "NOT_PACKET_SCOPED")


def invalid_packet_payload(result: PacketValidationResult, *, repair_attempted: bool) -> dict[str, Any]:
    return {
        "packet_gate": result.code,
        "valid": False,
        "reason": result.reason,
        "repair_attempted": bool(repair_attempted),
    }
