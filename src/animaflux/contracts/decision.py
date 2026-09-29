"""Decision / Planning 契约（v5.9 §14D）。

Decision = 现在选哪个方向；是 Process，不新增 Core State（§14D 核心定义）。
DecisionResult 是结构化 Cognitive Artifact（§14D.15）。四阶段：Framing → Candidate
Generation → Evaluation → Selection（§14D.4）。Satisficing（§14D.11），不用单一
Universal Utility Score（§14D.9）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionTriggerType(str, Enum):
    """决策触发来源（§12E）：外部事件 / 内部动机 / 排程（时间到点）。"""

    EXTERNAL = "external"
    INTERNAL = "internal"
    SCHEDULED = "scheduled"


@dataclass(frozen=True)
class DecisionFrame:
    """「当前到底在决定什么」（§14D.5）。"""

    frame_id: str
    decision_problem: str
    trigger_refs: tuple[str, ...] = ()
    trigger_type: str = DecisionTriggerType.EXTERNAL.value  # §12E：EXTERNAL / INTERNAL / SCHEDULED
    relevant_goal_refs: tuple[str, ...] = ()
    time_horizon: str = "immediate"
    urgency: float = 0.0
    known_constraints: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()


@dataclass(frozen=True)
class Candidate:
    """一个待评估候选（§14D.6）。source 为 habit / procedure / plan / environment / llm 等。"""

    candidate_id: str
    action_type: str
    description: str = ""
    source: str = "policy"
    feasibility: float = 1.0  # Subjective Feasibility（§14D.7），非客观可执行性


@dataclass(frozen=True)
class CandidateEvaluation:
    """结构化 Trade-off（§14D.9），不把全部意义压成单一总分。"""

    candidate_ref: str
    goal_supports: tuple[str, ...] = ()
    goal_conflicts: tuple[str, ...] = ()
    value_supports: tuple[str, ...] = ()
    value_conflicts: tuple[str, ...] = ()
    drive_supports: tuple[str, ...] = ()
    risk: float = 0.0
    uncertainty: float = 0.5
    feasibility: float = 1.0
    reversibility: float = 0.5
    urgency: float = 0.0
    emotional_bias: float = 0.0
    hard_violation: bool = False


@dataclass(frozen=True)
class DecisionResult:
    """Decision 输出（§14D.15）。Intent ≠ Result（§14D.16）。"""

    decision_id: str
    frame_ref: str
    selected_candidate_ref: str | None = None
    selected_intent: Any = None  # ActionIntent | CommunicativeIntent | None
    rejected_candidate_refs: tuple[str, ...] = ()
    major_tradeoffs: tuple[str, ...] = ()
    uncertainty: float = 0.5
    confidence: float = 0.5
    no_action_reason: str | None = None
    source_refs: tuple[str, ...] = ()
    trace: dict[str, Any] = field(default_factory=dict)
