"""Experience Index（Cross-cutting Developmental Context §7）。

Derived / Auxiliary Index，非 Source of Truth；可从 Memory Store 全量重建；更新失败不阻塞
Core Tick Commit（§7）。Experience 必须 Domain-specific（§4），禁止单一全局 experience_level。
Experience ≠ Competence ≠ Self-Efficacy（§6）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from animaflux.contracts.experience import DomainExperience, ExperienceProfileView
from animaflux.contracts.memory import MemoryEntry, MemoryVersion


def _latest(a: datetime | None, b: datetime | None) -> datetime | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


class ExperienceIndex:
    """domain -> DomainExperience 的派生索引。"""

    def __init__(self) -> None:
        self._domains: dict[str, DomainExperience] = {}

    def record(self, entry: MemoryEntry, version: MemoryVersion) -> None:
        """从一条逻辑 Memory（entry + 当前 version）派生领域阅历（可增量）。

        以 memory_id 为粒度：同一逻辑 Memory 的多次 Reconsolidation 不重复计 exposure。
        """
        if version.domain is None:
            return
        d = self._domains.get(version.domain)
        if d is None:
            d = DomainExperience(domain=version.domain)
        significant = (
            d.significant_episode_refs + (entry.memory_id,)
            if version.importance >= 0.7 and entry.memory_id not in d.significant_episode_refs
            else d.significant_episode_refs
        )
        procedural = (
            d.procedural_refs + (entry.memory_id,)
            if entry.memory_type == "procedural" and entry.memory_id not in d.procedural_refs
            else d.procedural_refs
        )
        self._domains[version.domain] = replace(
            d,
            exposure=d.exposure + 1,
            recency=_latest(d.recency, version.created_runtime_time),
            significant_episode_refs=significant,
            procedural_refs=procedural,
        )

    def rebuild(self, memories) -> None:
        """从 Source 全量重建（§7「应从历史 Source Rebuild」）。memories 迭代 (entry, version)。"""
        self._domains = {}
        for entry, version in memories:
            self.record(entry, version)

    def profile(self) -> ExperienceProfileView:
        return ExperienceProfileView(domains=tuple(sorted(self._domains.values(), key=lambda d: d.domain)))

    def domain(self, name: str) -> DomainExperience | None:
        return self._domains.get(name)
