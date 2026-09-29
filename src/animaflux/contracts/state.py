"""State 所有权契约（v5.9 §3 / §7.15 / §7.16）。

自己的状态自己解释：State Owner 根据 Influence Batch 计算 Next State。
一个 Namespace 恰好一个 Primary Owner（§3.3）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from animaflux.contracts.context import RuntimeContext
    from animaflux.contracts.influence import Influence


class StateNamespace(str, Enum):
    """13 个 Core State（v5.9 §2），已冻结，不再新增。"""

    IDENTITY = "identity"
    BODY = "body"
    PERSONALITY = "personality"
    EMOTION = "emotion"
    DRIVE = "drive"
    MEMORY = "memory"
    BELIEF = "belief"
    VALUE = "value"
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    WORLD_MODEL = "world_model"
    SELF_MODEL = "self_model"
    NARRATIVE = "narrative"


@dataclass
class StateResolutionResult:
    """State Owner 的 resolve 输出（§7.15）。trace 用于解释「为何 A→B」。"""

    next_state: Any
    emitted_influences: tuple = ()
    emitted_events: tuple = ()
    changed: bool = True
    trace: dict | None = None


class StateOwner(Protocol):
    """State Owner 概念接口（§7.16）。

    Kernel Resolver 只负责调用，不理解具体领域业务（Kernel routes, Owner interprets）。
    """

    def resolve(
        self,
        current_state: Any,
        influences: tuple["Influence", ...],
        context: "RuntimeContext",
    ) -> StateResolutionResult:
        ...
