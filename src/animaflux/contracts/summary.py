"""LifeSummaryView（v5.9 Web Plan §11）。

只读聚合 View，用于首页 / 列表页展示一个生命的概览。它不是新的 Core State，也不属于
Source-of-Truth；由 `LifeHandle.summary()` 从现有 Public Read View 派生（§Web Plan §10）。
字段只来自已 seed 的 Core State + Development Context；未接入生命循环的能力（Memory 索引、
Goal/Drive 等尚未 seed 的 State）以空集合呈现，前端据此省略展示。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class MoodSummary:
    valence: float
    arousal: float


@dataclass(frozen=True)
class HomeostasisSummary:
    energy: float
    hydration: float
    nutrition: float


@dataclass(frozen=True)
class LifeSummaryView:
    """一个数字生命当前状态的只读概览（§Web Plan §11）。"""

    life_id: str
    primary_name: str
    runtime_time: str
    vital_status: str
    chronological_age: timedelta
    life_stage: str
    mood: MoodSummary
    biological_age: float
    homeostasis: HomeostasisSummary
    self_esteem: float
    active_roles: tuple[str, ...] = ()
    relationship_targets: tuple[str, ...] = ()
    top_values: tuple[str, ...] = ()
    active_goals: tuple[str, ...] = ()
    top_drives: tuple[str, ...] = ()
    domain_experience: tuple[str, ...] = ()
