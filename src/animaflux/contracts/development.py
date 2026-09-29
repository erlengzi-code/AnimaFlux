"""Developmental Context 契约（Cross-cutting Developmental Context & Experience Modulation）。

核心定义：Age ≠ Experience ≠ Skill ≠ Self-Efficacy。本决策不新增第 14 个 Core State。
DevelopmentContextView 是 Derived View / Runtime Context，不是 Source-of-Truth State（§24.14）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Protocol

from animaflux.contracts.experience import ExperienceProfileView


@dataclass(frozen=True)
class DevelopmentContextView:
    """从真实生命历史派生的 Development Context（§24.14）。

    - chronological_age 由 Identity.birth_time + Runtime Time 派生（§24.3）；
    - biological_maturity 属于 Body（§24.4）；
    - life_stage 由可替换 LifeStagePolicy 派生（§24.5）；
    - domain_experience 从真实历史派生（§24.9），非 Source-of-Truth。
    """

    agent_id: str
    chronological_age: timedelta
    biological_maturity: float = 0.5
    life_stage: str = "unspecified"
    domain_experience: ExperienceProfileView = field(default_factory=ExperienceProfileView)
    role_refs: tuple[str, ...] = ()
    transition_refs: tuple[str, ...] = ()


class LifeStagePolicy(Protocol):
    """Life Stage 派生策略（§24.5 / §16D.28）：可替换，Core 不硬编码固定人类年龄段。"""

    def stage(self, context: "DevelopmentContextView") -> str: ...
