"""RuntimeContext 的最小落地实现（v5.9 §13.1）。

受控执行环境：数据版本 / 时间 / 随机性 / Capability 访问（§13）。Process/Plugin 通过
Context 读数据、用 Capability，不能通过它修改 Runtime 状态（§13.10）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from animaflux.contracts.context import ExecutionContext, RandomService, TimeContext
from animaflux.kernel.registry import CapabilityRegistry


@dataclass(frozen=True)
class RuntimeContextImpl:
    """满足 contracts.context.RuntimeContext Protocol 的最小不可变实现。"""

    execution: ExecutionContext
    time: TimeContext
    random: RandomService
    capabilities: CapabilityRegistry

    def capability(self, capability_id: str) -> Any:
        """§13.5：Capability 调用绑定当前 Context，返回注册的 Primary Provider。"""
        return self.capabilities.get(capability_id)
