from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuarantineEntry:
    action: str
    action_class: str
    reason: str


class QuarantineLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, action: str, action_class: str, reason: str) -> None:
        entry = QuarantineEntry(action=action, action_class=action_class, reason=reason)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
