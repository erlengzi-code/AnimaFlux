"""Kernel 注册表（v5.9 §9.7 Capability Registry / §3.3 Namespace Registry）。"""

from __future__ import annotations

from typing import Any

from animaflux.contracts.capability import CapabilityId


class CapabilityRegistry:
    """「能力通讯录」：capability_id -> Provider 列表（§9.7）。"""

    def __init__(self) -> None:
        self._providers: dict[CapabilityId, list[tuple[Any, str]]] = {}

    def register(self, capability_id: CapabilityId, provider: Any, *, version: str = "1.0") -> None:
        self._providers.setdefault(capability_id, []).append((provider, version))

    def get(self, capability_id: CapabilityId) -> Any:
        providers = self._providers.get(capability_id)
        if not providers:
            raise KeyError(f"no provider registered for capability '{capability_id}'")
        return providers[0][0]  # Primary = first registered（§9.8 第一版不随机选择）

    def providers(self, capability_id: CapabilityId) -> tuple[Any, ...]:
        return tuple(p for p, _ in self._providers.get(capability_id, ()))

    def has(self, capability_id: CapabilityId) -> bool:
        return capability_id in self._providers


class NamespaceRegistry:
    """namespace -> Primary Owner 映射（§3.3 一个 Namespace 一个 Owner）。"""

    def __init__(self) -> None:
        self._owners: dict[str, Any] = {}

    def register_owner(self, namespace: str, owner: Any) -> None:
        if namespace in self._owners:
            raise ValueError(f"namespace '{namespace}' already has a primary owner")
        self._owners[namespace] = owner

    def get_owner(self, namespace: str) -> Any:
        if namespace not in self._owners:
            raise KeyError(f"no owner registered for namespace '{namespace}'")
        return self._owners[namespace]

    def namespaces(self) -> tuple[str, ...]:
        return tuple(self._owners)
