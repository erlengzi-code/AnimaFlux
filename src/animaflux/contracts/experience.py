"""Experience 契约（Cross-cutting Developmental Context & Experience Modulation）。

Age ≠ Experience ≠ Skill ≠ Self-Efficacy（核心定义）。Experience 必须 Domain-specific（§4），
不设计单一全局 experience_level。ExperienceIndex 是 Derived / Auxiliary Index，非 Source of Truth，
可从历史 Source 重建（§7）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DomainExperience:
    """单个 Domain 的阅历画像（§5 ExperienceProfileView 的组成）。"""

    domain: str
    exposure: int = 0
    practice: int = 0
    diversity: int = 0
    recency: datetime | None = None
    success_count: int = 0
    failure_count: int = 0
    significant_episode_refs: tuple[str, ...] = ()
    procedural_refs: tuple[str, ...] = ()
    confidence: float = 0.5


@dataclass(frozen=True)
class ExperienceProfileView:
    """从真实生命历史派生的阅历快照（§5）。非 Source-of-Truth State。"""

    domains: tuple[DomainExperience, ...] = ()

    def domain(self, name: str) -> DomainExperience | None:
        for d in self.domains:
            if d.domain == name:
                return d
        return None
