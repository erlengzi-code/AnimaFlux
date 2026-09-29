"""Process 核心协议（v5.9 §12）。

Process = Runtime 中统一的可执行生命逻辑单元，run(context) -> ProcessResult（§12.4）。
Process 不直接修改 Core State（§12.5），只输出受控结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from animaflux.contracts.context import RuntimeContext
    from animaflux.contracts.event import Event
    from animaflux.contracts.influence import Influence


@dataclass
class ProcessResult:
    """Process 的受控输出（§12.7）。

    Action / Schedule Proposal 的具体类型在 P6 / P8 定义，此处先以 Any 占位。
    """

    events: tuple["Event", ...] = ()
    influences: tuple["Influence", ...] = ()
    actions: tuple[Any, ...] = ()
    schedule_proposals: tuple[Any, ...] = ()
    warnings: tuple[Any, ...] = ()
    trace: dict[str, Any] | None = None


class Process(Protocol):
    """Process 协议（§12.4）：统一 run(context) 调用模型。"""

    def run(self, context: "RuntimeContext") -> ProcessResult:
        ...
