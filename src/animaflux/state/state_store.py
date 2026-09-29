"""State Store Core（v5.9 §14）+ Snapshot Strategy（§15）。

State Owner 管「状态是什么意思、如何变化」，State Store 管「状态现在是哪一版、如何保存、
如何提交」（§14.2）。Committed Version 不可原地修改（§15.2）；只有变化的 Namespace 才创建
新版本（Namespace 级 Copy-on-Write，§15.4）；Tick 整体成功后才 Commit（§14.6）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from animaflux.contracts.state import StateNamespace
from animaflux.kernel.registry import NamespaceRegistry


@dataclass(frozen=True)
class StateVersion:
    """一条不可变状态版本（§15.2）。state 本身也必须是不可变对象（frozen dataclass）。"""

    namespace: StateNamespace
    version: int
    state: Any


class StateStore:
    """按 agent_id + namespace 管理三类版本：Committed / Tick Snapshot / Working（§14.5）。"""

    def __init__(self, agent_id: str, registry: NamespaceRegistry | None = None) -> None:
        self._agent_id = agent_id
        self._registry = registry
        self._committed: dict[StateNamespace, StateVersion] = {}
        self._snapshot: dict[StateNamespace, StateVersion] | None = None
        self._working: dict[StateNamespace, StateVersion] = {}
        self._next_version: dict[StateNamespace, int] = {}

    @property
    def agent_id(self) -> str:
        return self._agent_id

    # -- 初始状态（Agent 创建时，无 Tick） --
    def seed(self, namespace: StateNamespace, state: Any) -> StateVersion:
        if namespace in self._committed:
            raise ValueError(f"namespace '{namespace}' already seeded")
        version = StateVersion(namespace, 1, state)
        self._committed[namespace] = version
        self._next_version[namespace] = 2
        return version

    def restore_committed(self, namespace: StateNamespace, version: int, state: Any) -> StateVersion:
        """RESTORE（§21.1）：以给定版本号恢复已提交状态，不重置版本计数。"""
        if namespace in self._committed:
            raise ValueError(f"namespace '{namespace}' already restored")
        restored = StateVersion(namespace, version, state)
        self._committed[namespace] = restored
        self._next_version[namespace] = version + 1
        return restored

    # -- Tick 生命周期 --
    def begin_tick(self) -> None:
        """从 Committed 冻结出 Tick Snapshot（§14.5），Working 清空。"""
        self._snapshot = dict(self._committed)
        self._working = {}

    def commit(self) -> None:
        """Tick 整体成功后才把 Working 提升为 Committed（§14.6）。"""
        if self._snapshot is None:
            raise RuntimeError("commit() 只能在 active tick 中调用")
        self._committed.update(self._working)
        self._snapshot = None
        self._working = {}

    def rollback(self) -> None:
        """丢弃 Working；Committed 保持原样（§15.7 无需逐字段回改）。"""
        self._snapshot = None
        self._working = {}

    # -- 读 --
    def read_version(self, namespace: StateNamespace) -> StateVersion:
        """当前稳定视图：Working > Snapshot > Committed（§15.6 Round 读冻结版本）。"""
        if namespace in self._working:
            return self._working[namespace]
        if self._snapshot is not None and namespace in self._snapshot:
            return self._snapshot[namespace]
        return self._committed[namespace]

    def read(self, namespace: StateNamespace) -> Any:
        return self.read_version(namespace).state

    def committed_version(self, namespace: StateNamespace) -> StateVersion:
        return self._committed[namespace]

    def committed_namespaces(self) -> tuple[StateNamespace, ...]:
        """已 seed 的 Namespace（稳定排序，§22.5）。"""
        return tuple(sorted(self._committed, key=lambda n: n.value))

    # -- 写（Copy-on-Write） --
    def stage(self, namespace: StateNamespace, new_state: Any, *, owner: Any) -> StateVersion:
        """向 Working 写入候选新状态；仅 Primary Owner 有写入权（§3.3 / §3.10）。

        只有真正变化的 Namespace 才创建新版本（§15.4）。
        """
        self._require_owner(namespace, owner)
        current = self.read_version(namespace)
        if new_state is current.state:
            return current  # 未变，复用旧版本引用
        version = self._next_version.get(namespace, current.version + 1)
        self._next_version[namespace] = version + 1
        staged = StateVersion(namespace, version, new_state)
        self._working[namespace] = staged
        return staged

    def _require_owner(self, namespace: StateNamespace, owner: Any) -> None:
        if self._registry is None:
            return
        expected = self._registry.get_owner(namespace)
        if owner is not expected:
            raise PermissionError(
                f"非 Owner 不能写 '{namespace.value}'：{owner!r} 不是它的 Primary Owner"
            )
