from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nexusgate.memory.schema import MemoryRecord, QueryFilters


class StructuredMemoryRepository:
    STALE_DAYS = {"L2": 30, "L3": 60, "L4": 7}

    def __init__(self, structured_memory_path: Path, *, compact_threshold: int = 2000) -> None:
        self.structured_memory_path = structured_memory_path
        self.compact_threshold = compact_threshold
        self.structured_memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.structured_memory_path.exists():
            self.structured_memory_path.write_text("", encoding="utf-8")

    def load_all(self) -> list[MemoryRecord]:
        rows: list[MemoryRecord] = []
        try:
            lines = self.structured_memory_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                rows.append(MemoryRecord(**payload))
            except Exception:
                continue
        return rows

    def load_latest_map(self) -> dict[str, MemoryRecord]:
        latest: dict[str, MemoryRecord] = {}
        for row in self.load_all():
            latest[row.memory_id] = row
        return latest

    def upsert(self, record: MemoryRecord) -> MemoryRecord:
        with self.structured_memory_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(record.to_dict(), ensure_ascii=False)}\n")
        if self._line_count() >= self.compact_threshold:
            self.compact()
        return record

    def upsert_many(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        if not records:
            return []
        with self.structured_memory_path.open("a", encoding="utf-8") as handle:
            for row in records:
                handle.write(f"{json.dumps(row.to_dict(), ensure_ascii=False)}\n")
        if self._line_count() >= self.compact_threshold:
            self.compact()
        return records

    def get_by_ids(self, memory_ids: list[str]) -> list[MemoryRecord]:
        latest = self.load_latest_map()
        return [latest[mid] for mid in memory_ids if mid in latest]

    def filter_visible(self, filters: QueryFilters) -> list[MemoryRecord]:
        rows = self.load_latest_map().values()
        visible: list[MemoryRecord] = []
        allowed_scopes = set(filters.include_scopes or ["session", "project", "user", "global"])
        now = datetime.now(timezone.utc)
        for row in rows:
            if filters.layers and row.layer not in filters.layers:
                continue
            if row.scope not in allowed_scopes:
                continue
            if row.scope == "session" and filters.session_id and row.session_id != filters.session_id:
                continue
            if row.scope == "project":
                # Project-scoped records only visible when project_id matches
                if not filters.project_id or row.project_id != filters.project_id:
                    continue
            if filters.only_verified and not row.verified:
                continue
            if filters.exclude_archived and row.archived:
                continue
            if self._is_stale_unverified(row, now):
                continue
            visible.append(row)
        return visible

    def _is_stale_unverified(self, row: MemoryRecord, now: datetime) -> bool:
        if row.verified:
            return False
        limit_days = int(self.STALE_DAYS.get(row.layer, 90))
        if limit_days <= 0:
            return False
        ts_text = (row.updated_at or row.created_at or "").strip()
        if not ts_text:
            return False
        try:
            ts = datetime.fromisoformat(ts_text.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return False
        age_days = max((now - ts).days, 0)
        return age_days > limit_days

    def lexical_query(self, query: str, filters: QueryFilters, *, limit: int = 20) -> list[MemoryRecord]:
        lowered = (query or "").lower().strip()
        candidates: list[tuple[float, MemoryRecord]] = []
        for row in self.filter_visible(filters):
            score = row.confidence
            if lowered and lowered in row.content.lower():
                score += 2.0
            if row.verified:
                score += 1.0
            candidates.append((score, row))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in candidates[:limit]]

    def compact(self) -> int:
        latest = self.load_latest_map()
        rows = list(latest.values())
        rows.sort(key=lambda row: row.updated_at or row.created_at)
        content = "".join(f"{json.dumps(row.to_dict(), ensure_ascii=False)}\n" for row in rows)
        self.structured_memory_path.write_text(content, encoding="utf-8")
        return len(rows)

    def archive(self, memory_id: str) -> bool:
        latest = self.load_latest_map()
        row = latest.get(memory_id)
        if row is None:
            return False
        row.archived = True
        self.upsert(row)
        return True

    def _line_count(self) -> int:
        try:
            return len(self.structured_memory_path.read_text(encoding="utf-8").splitlines())
        except Exception:
            return 0
