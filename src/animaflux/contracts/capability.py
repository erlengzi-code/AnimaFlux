"""Capability 契约（v5.9 §9）。

Capability = Plugin 对外公开的标准能力接口；依赖能力，不依赖实现（§9.1）。
要数据用 Capability，要改变别人用 Influence（§9.2）。
具体能力用子 Protocol 表达（§9.14），返回 frozen View / DTO，不暴露内部 State（§9.15）。
"""

from __future__ import annotations

from typing import Any, Protocol

CapabilityId = str  # 例如 "body.status" / "memory.search" / "llm.chat" / "world.query"


class CapabilityRegistry(Protocol):
    """§9.7 Kernel 维护的「能力通讯录」。调用方只查询 Registry，不自行找具体 Plugin。

    一个 Capability 可以有多个 Provider，Runtime 选择 Primary Provider（§9.8）。
    """

    def register(
        self,
        capability_id: CapabilityId,
        provider: Any,
        *,
        version: str = "1.0",
    ) -> None:
        """注册一个 Provider。相同 capability_id 必须遵守相同 Contract（§9.13）。"""
        ...

    def get(self, capability_id: CapabilityId) -> Any:
        """返回 Primary Provider；无 Provider 时抛错。"""
        ...

    def providers(self, capability_id: CapabilityId) -> tuple[Any, ...]:
        """返回该 capability 的所有 Provider。"""
        ...

    def has(self, capability_id: CapabilityId) -> bool:
        ...
