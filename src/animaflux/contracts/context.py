"""Runtime Context 契约（v5.9 §13）。

受控执行环境：数据版本 / 权限 / 时间 / 可见性 / 随机性 / Trace 边界（§13）。
Process 通过 ProcessResult 输出，不能通过修改 Context 偷偷改变 Runtime（§13.10）。
StateView / EventView / WorldView 的具体 API 在 P3 落地。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ExecutionContext:
    """§13.2：一次 Process 执行的定位信息。"""

    runtime_id: str
    agent_id: str
    tick_id: str
    plugin_id: str
    process_id: str
    phase: str
    resolution_round: int = 0


@dataclass(frozen=True)
class TimeContext:
    """§13.3：所有生命逻辑基于 World Time，不用服务器真实时间（§22.7）。"""

    world_time: datetime
    delta_time: timedelta


class RandomStream(Protocol):
    """一条独立随机流（§22.4）。"""

    def random(self) -> float:
        """[0, 1) 均匀随机。"""
        ...

    def uniform(self, a: float, b: float) -> float:
        ...

    def randint(self, a: int, b: int) -> int:
        ...

    def choice(self, seq: Sequence[Any]) -> Any:
        ...


class RandomService(Protocol):
    """§13.7 / §22.3：由 Kernel 管理 Seed 的随机服务，支持 Replay / 实验 / Debug。

    按 (runtime / branch / agent / domain) 派生隔离的 Random Stream（§22.4）。
    """

    def stream(self, *parts: str) -> RandomStream:
        ...


class RuntimeContext(Protocol):
    """§13.1 受控执行环境的访问接口。"""

    execution: ExecutionContext
    time: TimeContext
    random: RandomService

    def capability(self, capability_id: str) -> Any:
        """§13.5：Capability 调用必须绑定当前 Context，不能自行读「最新状态」。"""
        ...
