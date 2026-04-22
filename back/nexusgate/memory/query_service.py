from __future__ import annotations

from nexusgate.memory.index import MemoryIndex
from nexusgate.memory.scoring import MemoryScorer
from nexusgate.memory.schema import MemoryRecord, QueryFilters
from nexusgate.memory.repository import StructuredMemoryRepository


class MemoryQueryService:
    def __init__(self, repository: StructuredMemoryRepository, index: MemoryIndex, scorer: MemoryScorer) -> None:
        self.repository = repository
        self.index = index
        self.scorer = scorer

    def query(self, *, query: str, filters: QueryFilters, limit: int) -> list[MemoryRecord]:
        visible = self.repository.filter_visible(filters)
        by_id = {row.memory_id: row for row in visible}
        ids = self.index.query(query, filters, limit=max(limit * 2, limit))
        merged: list[MemoryRecord] = [by_id[mid] for mid in ids if mid in by_id]
        if len(merged) < limit:
            lexical = self.repository.lexical_query(query, filters, limit=max(limit * 2, limit))
            for row in lexical:
                if row.memory_id not in {item.memory_id for item in merged}:
                    merged.append(row)
        scored = self.scorer.score(
            query=query,
            candidates=merged or visible,
            task_type="chat",
            current_session_id=filters.session_id,
            current_project_id=filters.project_id,
        )
        ranked_ids = [item.memory_id for item in scored]
        ranked_map = {row.memory_id: row for row in (merged or visible)}
        return [ranked_map[mid] for mid in ranked_ids if mid in ranked_map][:limit]

    def query_by_layers(
        self,
        *,
        query: str,
        filters: QueryFilters,
        limit_per_layer: int = 12,
    ) -> dict[str, list[MemoryRecord]]:
        out: dict[str, list[MemoryRecord]] = {}
        for layer in filters.layers:
            layer_filters = QueryFilters(
                layers=[layer],
                session_id=filters.session_id,
                project_id=filters.project_id,
                include_scopes=list(filters.include_scopes),
                only_verified=filters.only_verified,
                exclude_archived=filters.exclude_archived,
            )
            out[layer] = self.query(query=query, filters=layer_filters, limit=limit_per_layer)
        return out

    @staticmethod
    def render_layer_block(records: list[MemoryRecord]) -> str:
        if not records:
            return "(empty)"
        return "\n".join(record.content for record in records if record.content.strip()) or "(empty)"
