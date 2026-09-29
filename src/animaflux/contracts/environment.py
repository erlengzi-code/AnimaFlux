"""Environment 契约（v5.9 §31 / §32 / §33）。

Environment Adapter 是 AnimaFlux 与外部世界之间的转换插头（§31.1），不模拟世界（§31.3）。
External Event 与 Observation 分离（§32.2 / §32.3）；Action Intent 与 Action Result 分离（§33.1）。
外部输入不能直接写入主观 State，必须经 Perception → Appraisal → Influence → Resolver（§32.5）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from animaflux.contracts.decision import DecisionResult
from animaflux.contracts.event import Event


@dataclass(frozen=True)
class Observation:
    """Observation = 当前 Agent 实际可以接触到的信息（§32.3）。

    clarity / noise / intensity 是客观信号属性，供 Perception 的 Sensory Gate / Misperception
    机制使用（§14A.5）。Observation 表示感知机会，不代表真正注意到（§14A.18.3）。
    """

    observation_id: str
    modality: str  # visual / auditory / tactile / communication / interoception
    content: Any
    world_time: datetime
    source_entity: str | None = None
    clarity: float = 1.0
    noise: float = 0.0
    intensity: float = 0.5
    source_event_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationBatch:
    """一次 Tick 归一化后的 Environment Input（§15B.4）。"""

    observations: tuple[Observation, ...]
    world_time: datetime
    environment_context: dict[str, Any] = field(default_factory=dict)  # §32.4 location / nearby / ...


@dataclass(frozen=True)
class ActionIntent:
    """Agent 的行动意图（§33.2）；不裁决世界规则（§33.4）。

    §12E 增补：initiative 标记主动/被动来源（proactive / reactive）；goal_refs /
    motivation_refs 记录「为什么想做」；expected_outcome 是主观预期，不是世界真相。
    """

    intent_id: str
    actor: str
    action_type: str
    world_time: datetime
    target: str | None = None
    content: Any = None
    motivation_refs: tuple[str, ...] = ()
    initiative: str | None = None  # §12E：proactive | reactive | None
    goal_refs: tuple[str, ...] = ()
    expected_outcome: Any = None  # 主观预期（§12E），与 ActionResult.consequence（客观）分离


@dataclass(frozen=True)
class ActionResult:
    """外部环境对 Action Intent 的结果（§33.3）。"""

    result_id: str
    intent_id: str
    status: str  # success / failure / partial / blocked / delayed
    world_time: datetime
    consequence: Any = None
    observations: tuple[Observation, ...] = ()
    new_events: tuple[Event, ...] = ()


@dataclass(frozen=True)
class AgencyDecisionRecord:
    """一次主动决策的「为什么」叙事（§12E A8 Web Timeline / Why）。

    属于运行时内存叙事（不入 Commit Journal / Checkpoint），供 Web「为什么这样做」展示。
    """

    decision_id: str
    world_time: datetime
    trigger_type: str  # internal | scheduled
    relevant_goal_refs: tuple[str, ...] = ()
    motivation_refs: tuple[str, ...] = ()
    selected_action_type: str | None = None  # None 表示 NO_ACTION
    initiative: str | None = None
    expected_outcome: Any = None
    confidence: float = 0.5
    no_action_reason: str | None = None


@dataclass(frozen=True)
class AgencyOutcome:
    """LifeHandle.act() 的一次主动决策机会的完整结果（§12E）。"""

    acted: bool
    decision: DecisionResult | None = None
    intent: ActionIntent | None = None
    action_result: ActionResult | None = None
    tick_id: str | None = None


class EnvironmentAdapter(Protocol):
    """§31.2：转换输入 / 转换输出 / 信息边界 / 时间对齐 / 标识映射。"""

    def poll_observations(self, world_time: datetime) -> ObservationBatch:
        """拉取当前 World Time 下该 Agent 可见的 Observation（§32.3）。"""
        ...

    def submit_action(self, intent: ActionIntent) -> ActionResult:
        """把 Action Intent 交给外部世界，返回结果（§33.3）。"""
        ...

    def supported_actions(self) -> frozenset[str]:
        """§12E：本环境支持的动作词汇（prepare_task / seek_feedback / communicate / …）。"""
        ...

    def resolve_action(self, intent: ActionIntent, context: Any = None) -> ActionResult:
        """§12E：解析 Action Intent → 改变外部世界状态并返回 Observation（不写 Core State）。"""
        ...
