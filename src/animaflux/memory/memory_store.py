"""Memory Specialized Store（v5.9 §13F.8 / §16B.12–16B.15）。

Memory 不存入不断膨胀的大 State JSON，而是三分离：
memory_entry（哪一条逻辑 Memory）/ memory_version（现在如何记得）/ memory_runtime_state（机械检索元数据）。
Memory Store 是 Source of Truth（§13F.9）。Reconsolidation 出新版本不覆盖（§16B.14）；
Forgetting ≈ Accessibility Decay，不是 Delete（§13F.15）；retrieving ≠ rewriting（§16B.15）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from animaflux.contracts.memory import MemoryEntry, MemoryRuntimeState, MemoryVersion
from animaflux.kernel.ids import IdGenerator


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


class MemoryStore:
    """Specialized Memory Store。本实现为进程内（v0.1）；SQLite 耐久表在后续阶段接入。"""

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id
        self._entries: dict[str, MemoryEntry] = {}
        self._versions: dict[str, MemoryVersion] = {}  # version_id -> version
        self._version_list: dict[str, list[str]] = {}  # memory_id -> [version_id ...]
        self._runtime: dict[str, MemoryRuntimeState] = {}
        self._ids = IdGenerator("MEM", width=None)

    # -- 写：Memory Formation / Reconsolidation / Forgetting（§13F.6 / §13F.18 / §13F.15） --
    def form(
        self,
        memory_type: str,
        content: Any,
        *,
        summary_text: str | None = None,
        confidence: float = 0.5,
        importance: float = 0.5,
        emotional_salience: float = 0.0,
        source_refs: tuple[str, ...] = (),
        provenance: str | None = None,
        domain: str | None = None,
        tick_id: str | None = None,
        runtime_time: datetime | None = None,
    ) -> str:
        memory_id = self._ids.next()
        version_id = f"{memory_id}_v1"
        entry = MemoryEntry(
            memory_id=memory_id, agent_id=self._agent_id, memory_type=memory_type,
            created_tick_id=tick_id, current_version_id=version_id,
        )
        version = MemoryVersion(
            memory_version_id=version_id, memory_id=memory_id, revision=1, content=content,
            summary_text=summary_text, confidence=confidence, importance=importance,
            emotional_salience=emotional_salience, source_refs=tuple(source_refs),
            provenance=provenance, domain=domain, created_tick_id=tick_id,
            created_runtime_time=runtime_time,
        )
        self._entries[memory_id] = entry
        self._versions[version_id] = version
        self._version_list[memory_id] = [version_id]
        self._runtime[memory_id] = MemoryRuntimeState(memory_id=memory_id)
        return memory_id

    def reconsolidate(
        self,
        memory_id: str,
        *,
        content: Any = None,
        summary_text: str | None = None,
        confidence: float | None = None,
        importance: float | None = None,
        emotional_salience: float | None = None,
        source_refs: tuple[str, ...] | None = None,
        provenance: str | None = None,
        domain: str | None = None,
        tick_id: str | None = None,
        runtime_time: datetime | None = None,
    ) -> str:
        """Reconsolidation 创建新 Version，不覆盖旧 Content（§13F.18 / §16B.14）。"""
        entry = self._entries[memory_id]
        cur = self.get_current_version(memory_id)
        new_version_id = f"{memory_id}_v{cur.revision + 1}"
        new_version = MemoryVersion(
            memory_version_id=new_version_id, memory_id=memory_id, revision=cur.revision + 1,
            content=cur.content if content is None else content,
            summary_text=cur.summary_text if summary_text is None else summary_text,
            confidence=cur.confidence if confidence is None else confidence,
            importance=cur.importance if importance is None else importance,
            emotional_salience=cur.emotional_salience if emotional_salience is None else emotional_salience,
            source_refs=cur.source_refs if source_refs is None else tuple(source_refs),
            provenance=cur.provenance if provenance is None else provenance,
            domain=cur.domain if domain is None else domain,
            created_tick_id=tick_id, created_runtime_time=runtime_time,
            parent_version_id=cur.memory_version_id,
        )
        self._versions[new_version_id] = new_version
        self._version_list[memory_id].append(new_version_id)
        self._entries[memory_id] = replace(entry, current_version_id=new_version_id)
        return new_version_id

    def decay_accessibility(
        self,
        memory_id: str,
        *,
        factor: float | None = None,
        tick_id: str | None = None,
    ) -> None:
        """Forgetting ≈ Accessibility Decay（§13F.15），不是 DELETE。Memory 内容仍在。"""
        rt = self._runtime[memory_id]
        new_accessibility = _clamp01(rt.accessibility * factor) if factor is not None else rt.accessibility
        self._runtime[memory_id] = replace(rt, accessibility=new_accessibility, updated_tick_id=tick_id)

    def record_retrieval(self, memory_id: str, *, runtime_time: datetime | None = None) -> None:
        """检索后 bounded 提升 accessibility（§14C.13）；不修改 Memory 内容（§16B.15）。"""
        rt = self._runtime[memory_id]
        self._runtime[memory_id] = replace(
            rt,
            accessibility=_clamp01(rt.accessibility + 0.05),
            retrieval_count=rt.retrieval_count + 1,
            last_retrieved_runtime_time=runtime_time,
        )

    # -- 读：Source of Truth 访问（由 Memory 模块内部 / Retrieval Process 使用） --
    def get_entry(self, memory_id: str) -> MemoryEntry:
        return self._entries[memory_id]

    def get_version(self, version_id: str) -> MemoryVersion:
        return self._versions[version_id]

    def get_current_version(self, memory_id: str) -> MemoryVersion:
        return self._versions[self._entries[memory_id].current_version_id]

    def list_versions(self, memory_id: str) -> tuple[MemoryVersion, ...]:
        return tuple(self._versions[vid] for vid in self._version_list[memory_id])

    def current_runtime_state(self, memory_id: str) -> MemoryRuntimeState:
        return self._runtime[memory_id]

    def iter_entries(self) -> tuple[MemoryEntry, ...]:
        return tuple(self._entries.values())

    def iter_all_versions(self) -> tuple[MemoryVersion, ...]:
        """按创建顺序返回全部版本，供 ExperienceIndex 等 Derived Index 重建。"""
        return tuple(
            self._versions[vid]
            for vids in self._version_list.values()
            for vid in vids
        )

    def iter_current_memories(self) -> tuple[tuple[MemoryEntry, MemoryVersion], ...]:
        """按 form 顺序返回 (entry, current_version)，供 Derived Index 以逻辑 Memory 粒度重建。"""
        return tuple(
            (entry, self._versions[entry.current_version_id])
            for entry in self._entries.values()
        )
