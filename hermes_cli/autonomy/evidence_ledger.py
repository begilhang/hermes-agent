from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceEntry:
    source: str
    status: str
    observation: str
    data: dict[str, Any] | None = None


class EvidenceLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, source: str, status: str, observation: str, data: dict[str, Any] | None = None) -> None:
        entry = EvidenceEntry(source=source, status=status, observation=observation, data=data)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False, default=str) + "\n")
