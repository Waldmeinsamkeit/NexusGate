from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MemoryEvent:
    event_type: str
    memory_id: str = ""
    candidate_id: str = ""
    session_id: str = ""
    layer: str = ""
    status: str = ""
    created_at: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class MemoryEventLogger:
    def __init__(self, event_path: Path) -> None:
        self.event_path = event_path
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.event_path.exists():
            self.event_path.write_text("", encoding="utf-8")

    def append(self, event: MemoryEvent) -> None:
        if not event.created_at:
            event.created_at = datetime.now(timezone.utc).isoformat()
        with self.event_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(asdict(event), ensure_ascii=False)}\n")

    def append_many(self, events: list[MemoryEvent]) -> None:
        for event in events:
            self.append(event)
