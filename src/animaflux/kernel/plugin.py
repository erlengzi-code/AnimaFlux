"""Kernel Plugin 管理（v5.9 §11）。

Plugin = 功能模块 / 插件包；Manifest 是静态声明，不保存 Runtime State（§11.11）。
生命周期 Installed → ... → Unloaded（§11.6）；启动前 Fail Fast 校验（§11.8）。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any


class LifecycleStage(str, Enum):
    INSTALLED = "installed"
    DISCOVERED = "discovered"
    ENABLED = "enabled"
    VALIDATED = "validated"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    UNLOADED = "unloaded"


@dataclass(frozen=True)
class PluginManifest:
    """§11.11 静态只读声明。"""

    plugin_id: str
    name: str
    version: str
    kernel_compatibility: str

    owns_states: tuple[str, ...] = ()
    provides_capabilities: tuple[str, ...] = ()
    requires_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()

    hooks: tuple[str, ...] = ()
    task_types: tuple[str, ...] = ()

    state_schema_version: int | None = None


class Plugin:
    """Manifest + 实例 + 当前生命周期阶段。"""

    def __init__(self, manifest: PluginManifest, instance: Any = None) -> None:
        self.manifest = manifest
        self.instance = instance
        self.stage = LifecycleStage.DISCOVERED


class PluginManager:
    """插件发现 / 注册 / 校验 / 依赖排序（Kernel 机制，不理解业务语义）。"""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def add(self, plugin: Plugin) -> None:
        pid = plugin.manifest.plugin_id
        if pid in self._plugins:
            raise ValueError(f"duplicate plugin_id '{pid}'")
        self._plugins[pid] = plugin

    def get(self, plugin_id: str) -> Plugin:
        return self._plugins[plugin_id]

    def plugins(self) -> tuple[Plugin, ...]:
        return tuple(self._plugins.values())

    # ---- Validation（§11.8 Fail Fast，启动前发现结构问题）----
    def validate(self) -> list[str]:
        errors: list[str] = []
        errors.extend(self._check_owner_conflicts())
        errors.extend(self._check_task_type_conflicts())
        errors.extend(self._check_required_capabilities())
        if self._has_dependency_cycle():
            errors.append("required dependency graph contains a cycle")
        return errors

    def _check_owner_conflicts(self) -> list[str]:
        seen: dict[str, str] = {}
        errors: list[str] = []
        for p in self._plugins.values():
            for ns in p.manifest.owns_states:
                if ns in seen:
                    errors.append(
                        f"state namespace '{ns}' owned by both '{seen[ns]}' and '{p.manifest.plugin_id}'"
                    )
                else:
                    seen[ns] = p.manifest.plugin_id
        return errors

    def _check_task_type_conflicts(self) -> list[str]:
        seen: dict[str, str] = {}
        errors: list[str] = []
        for p in self._plugins.values():
            for tt in p.manifest.task_types:
                if tt in seen:
                    errors.append(
                        f"task_type '{tt}' provided by both '{seen[tt]}' and '{p.manifest.plugin_id}'"
                    )
                else:
                    seen[tt] = p.manifest.plugin_id
        return errors

    def _capability_providers(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for p in self._plugins.values():
            for cap in p.manifest.provides_capabilities:
                result.setdefault(cap, p.manifest.plugin_id)
        return result

    def _check_required_capabilities(self) -> list[str]:
        providers = self._capability_providers()
        errors: list[str] = []
        for p in self._plugins.values():
            for cap in p.manifest.requires_capabilities:
                if cap not in providers:
                    errors.append(
                        f"plugin '{p.manifest.plugin_id}' requires missing capability '{cap}'"
                    )
        return errors

    def _dependency_graph(self) -> tuple[dict[str, list[str]], dict[str, int]]:
        """A requires X、B provides X => A 依赖 B => 边 B -> A（B 先初始化）。"""
        providers = self._capability_providers()
        adjacency: dict[str, list[str]] = {pid: [] for pid in self._plugins}
        indegree: dict[str, int] = {pid: 0 for pid in self._plugins}
        for p in self._plugins.values():
            deps: set[str] = set()
            for cap in p.manifest.requires_capabilities:
                provider = providers.get(cap)
                if provider and provider != p.manifest.plugin_id:
                    deps.add(provider)
            for dep in deps:
                adjacency[dep].append(p.manifest.plugin_id)
                indegree[p.manifest.plugin_id] += 1
        return adjacency, indegree

    def _topological_order(self) -> list[str]:
        adjacency, indegree = self._dependency_graph()
        queue = deque(pid for pid, deg in indegree.items() if deg == 0)
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in adjacency[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        return order

    def _has_dependency_cycle(self) -> bool:
        return len(self._topological_order()) != len(self._plugins)

    def ordered_plugin_ids(self) -> list[str]:
        """依赖优先的拓扑顺序（§11.10）。"""
        return self._topological_order()
