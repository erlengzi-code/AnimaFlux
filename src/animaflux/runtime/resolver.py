"""State Resolver（v5.9 §7）。

Resolver 只负责「组织计算」：Influence 分组 / Owner 查找 / Resolution Round / Working State
管理 / 确定性 / Deferred Influence（§7.3）。领域数学由 State Owner 负责（§7.4）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from animaflux.contracts.context import RuntimeContext
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.kernel.registry import NamespaceRegistry
from animaflux.state.state_store import StateStore

DEFAULT_MAX_ROUNDS = 3  # §7.8 Runtime 安全阀，不代表心理因果只有三层


@dataclass(frozen=True)
class ResolutionOutcome:
    """一次 resolve() 的结果。ok=False 时调用方应 rollback（§7.12）。"""

    ok: bool
    rounds_run: int
    changed_namespaces: tuple[StateNamespace, ...]
    deferred_count: int
    error: str | None = None


class InfluenceBuffer:
    """当前 Tick 的 Influence 缓冲（§7.2「先收齐，再统一分组」）。"""

    def __init__(self) -> None:
        self._items: list[Influence] = []

    def add(self, influence: Influence) -> None:
        self._items.append(influence)

    def add_many(self, influences: Iterable[Influence]) -> None:
        self._items.extend(influences)

    def __len__(self) -> int:
        return len(self._items)

    def drain(self) -> tuple[Influence, ...]:
        items = tuple(self._items)
        self._items.clear()
        return items


class StateResolver:
    """组织一个 Tick 内多条 Influence 对各个 State 的计算（§7.1）。"""

    def __init__(
        self,
        store: StateStore,
        registry: NamespaceRegistry,
        *,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
    ) -> None:
        self._store = store
        self._registry = registry
        self._max_rounds = max_rounds
        self._deferred: list[Influence] = []  # Deferred Influence Queue（§7.10），跨 Tick 保留

    @property
    def deferred_count(self) -> int:
        return len(self._deferred)

    def resolve(
        self,
        influences: Iterable[Influence],
        context: RuntimeContext,
    ) -> ResolutionOutcome:
        """把 influences（连同上一 Tick 遗留的 deferred）经有限轮次裁决进 Working State。

        达到 max_rounds 后仍产生的新 Influence 进入 Deferred Queue（§7.10），后续 Tick 继续。
        """
        pending: list[Influence] = list(self._deferred)
        self._deferred.clear()
        pending.extend(influences)

        changed: set[StateNamespace] = set()
        rounds_run = 0
        try:
            while rounds_run < self._max_rounds:
                if not pending:  # §7.9 停止条件：本轮没有新 Influence
                    break
                rounds_run += 1
                next_pending: list[Influence] = []
                for namespace, group in self._group(pending):
                    owner = self._registry.get_owner(namespace)
                    current = self._store.read(namespace)
                    result = owner.resolve(current, group, context)
                    if result.changed:
                        self._store.stage(namespace, result.next_state, owner=owner)
                        changed.add(namespace)
                    next_pending.extend(result.emitted_influences)
                pending = next_pending
            self._deferred.extend(pending)
        except Exception as exc:  # §7.12：Owner 异常 → 本 Tick 不 Commit，回滚到 Snapshot
            self._deferred.extend(pending)
            return ResolutionOutcome(
                ok=False,
                rounds_run=rounds_run,
                changed_namespaces=(),
                deferred_count=len(self._deferred),
                error=str(exc),
            )
        return ResolutionOutcome(
            ok=True,
            rounds_run=rounds_run,
            changed_namespaces=tuple(sorted(changed, key=lambda n: n.value)),
            deferred_count=len(self._deferred),
        )

    def _group(
        self,
        influences: list[Influence],
    ) -> list[tuple[StateNamespace, tuple[Influence, ...]]]:
        """按 target_state 分组 + 稳定排序（§7.6：到达顺序不能决定业务结果）。"""
        ordered = sorted(
            influences,
            key=lambda i: (i.target_state, i.created_at, i.influence_id),
        )
        grouped: dict[StateNamespace, list[Influence]] = {}
        for inf in ordered:
            grouped.setdefault(StateNamespace(inf.target_state), []).append(inf)
        return [(ns, tuple(items)) for ns, items in grouped.items()]
