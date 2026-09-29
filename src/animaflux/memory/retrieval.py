"""Memory Retrieval Process + Capability（v5.9 §14C / §13F.24）。

Memory Retrieval 是 Process，不新增 Core State（§14C）。检索默认 read-only（§14C.13）；
RetrievedMemorySet 是临时 Cognitive Artifact（§14C.11）。权重属于 MemoryRetrievalPolicy
（§14C.22.6）。其他模块不能 memory_store.get_all()，只能经 Memory Retrieval Capability
获得受限 RetrievedMemorySet（§13F.24）。

v0.1 语义信号用确定性 keyword overlap（§14C.20 Vector Index 故障可降级到 keyword）。
"""

from __future__ import annotations

from typing import Any

from animaflux.contracts.memory import (
    MemoryRetrievalRequest,
    RetrievedMemory,
    RetrievedMemorySet,
)


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return f"{content.get('type', '')} {content.get('text', '')} {content.get('title', '')}"
    return str(content)


class MemoryRetrievalProcess:
    """确定性、预算化的检索（§14C）。"""

    def retrieve(self, request: MemoryRetrievalRequest, store) -> RetrievedMemorySet:
        candidates = []
        for entry in store.iter_entries():
            if entry.status != "active":
                continue
            if request.memory_types and entry.memory_type not in request.memory_types:
                continue
            version = store.get_current_version(entry.memory_id)
            runtime = store.current_runtime_state(entry.memory_id)
            if runtime.accessibility < request.min_accessibility:
                continue  # Stored ≠ Currently Retrievable（§14C.5）
            score = self._score(request, version, runtime)
            candidates.append((score, entry, version, runtime))

        candidates.sort(key=lambda t: (-t[0], t[1].memory_id))
        selected = candidates[: request.memory_count_budget]
        memories = tuple(
            self._to_retrieved(score, entry, version, runtime)
            for score, entry, version, runtime in selected
        )
        status = "NOT_FOUND" if not memories else ("PARTIAL" if len(candidates) > len(memories) else "FOUND")
        return RetrievedMemorySet(
            memories=memories,
            status=status,
            budget_used=len(memories),
            trace={"candidates": len(candidates), "selected": len(memories)},
        )

    def _score(self, request: MemoryRetrievalRequest, version, runtime) -> float:
        semantic = self._semantic_similarity(request.query, version.content)
        # §14C.22.5：综合语义、可访问性、重要度、情绪
        return (
            0.4 * semantic
            + 0.25 * runtime.accessibility
            + 0.25 * version.importance
            + 0.1 * version.emotional_salience
        )

    @staticmethod
    def _semantic_similarity(query: str, content: Any) -> float:
        if not query:
            return 0.0
        tokens = set(query.lower().split())
        if not tokens:
            return 0.0
        text = _to_text(content).lower()
        hits = sum(1 for t in tokens if t in text)
        return hits / len(tokens)

    @staticmethod
    def _to_retrieved(score: float, entry, version, runtime) -> RetrievedMemory:
        return RetrievedMemory(
            memory_id=entry.memory_id,
            memory_type=entry.memory_type,
            revision=version.revision,
            content=version.content,
            summary_text=version.summary_text,
            confidence=version.confidence,
            importance=version.importance,
            emotional_salience=version.emotional_salience,
            accessibility=runtime.accessibility,
            retrieval_score=score,
            source_refs=version.source_refs,
            provenance=version.provenance,
        )


class MemoryRetrievalCapability:
    """§13F.24：其他模块的唯一受限访问入口，禁止 get_all。"""

    def __init__(self, store, process: MemoryRetrievalProcess | None = None) -> None:
        self._store = store
        self._process = process or MemoryRetrievalProcess()

    def retrieve(self, request: MemoryRetrievalRequest) -> RetrievedMemorySet:
        return self._process.retrieve(request, self._store)
