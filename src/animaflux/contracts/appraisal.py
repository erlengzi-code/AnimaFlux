"""Appraisal 契约（v5.9 §14B）。

Appraisal 是 Process，不新增 Core State（§14B 核心定义）。
AppraisalResult 是 Cognitive Artifact，不是 State Mutation（§14B.9）。
多维 Appraisal，不压缩成单一正负分（§14B.1 / §14B.8）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AppraisableItem:
    """Appraisal 的通用输入项（§14B.5）：PerceivedEvent / Memory / Predicted Outcome 等。"""

    item_ref: str
    item_type: str  # perceived_event / memory / predicted_outcome / internal_signal / ...
    content: Any
    salience: float = 0.5
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoalImpact:
    """Appraisal 对单个 Goal 的影响 Facet（§14B.6）。"""

    goal_ref: str
    impact: str  # facilitate / thwart / conflict
    significance: float
    reason: str = ""


@dataclass(frozen=True)
class AppraisalResult:
    """一个 AppraisableItem 的多维评估结果（§14B.6）。overall_significance 不替代具体 Facets。"""

    appraisal_id: str
    appraisable_item_ref: str
    relevance: float
    overall_significance: float
    novelty: float = 0.0
    expectedness: float = 0.5
    goal_impacts: tuple[GoalImpact, ...] = ()
    value_impacts: tuple[Any, ...] = ()
    self_impacts: tuple[Any, ...] = ()
    relationship_impacts: tuple[Any, ...] = ()
    drive_need_impacts: tuple[Any, ...] = ()
    attribution: str | None = None
    controllability: float | None = None
    coping_potential: float | None = None
    certainty: float = 0.5
    urgency: float = 0.0
    anticipated_consequences: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()  # threat / loss / opportunity / gain（§14B.14.10 默认 Tags，Core 不写死）
    confidence: float = 0.5
    reason_codes: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    reappraisal_of: str | None = None
