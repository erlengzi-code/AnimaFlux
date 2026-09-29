"""Life Branch（v5.9 §21 / §22.11）。

Life Branch = 从历史 Checkpoint Fork 出的新演化轨迹。Fork 前 State Version 可共享（§21.8），
Fork 后各 Branch 独立增长、互不污染；从历史节点重新运行 Life Loop 必须创建新 Branch，不能
覆盖原历史（§21.4）。单独复制 Agent 是 Export / Clone，不是 Life Branch（§21.7）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from animaflux.contracts.context import RuntimeContext
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.kernel.ids import IdGenerator
from animaflux.kernel.registry import NamespaceRegistry
from animaflux.runtime.checkpoint import Checkpoint
from animaflux.runtime.resolver import StateResolver
from animaflux.state.state_store import StateStore

RANDOM_MODES = ("deterministic", "fresh_random")  # §21.10


@dataclass(frozen=True)
class BranchRecord:
    """Branch 元数据（§21.9）。"""

    branch_id: str
    parent_branch_id: str | None
    fork_checkpoint_id: str
    fork_world_time: str
    created_at: str
    branch_name: str
    description: str
    random_mode: str
    pinned: bool


class LifeBranch:
    """从 Checkpoint Fork 出的独立分支：共享 pre-fork 状态，post-fork 各自增长（§21.8）。"""

    def __init__(self, record: BranchRecord, checkpoint: Checkpoint, registry: NamespaceRegistry) -> None:
        self.record = record
        self.checkpoint = checkpoint
        # 分支拥有自己的 StateStore，但以 Checkpoint 的不可变状态对象做种子（共享引用，§21.8）
        self.store = StateStore(checkpoint.agent_id, registry=registry)
        for ns_value, state in checkpoint.states.items():
            self.store.seed(StateNamespace(ns_value), state)
        self.resolver = StateResolver(self.store, registry)

    def step(self, influences: Iterable[Influence], context: RuntimeContext | None = None):
        """在分支内独立演化一个 Tick；失败 rollback，不影响其它分支。"""
        self.store.begin_tick()
        outcome = self.resolver.resolve(tuple(influences), context)
        if not outcome.ok:
            self.store.rollback()
            raise RuntimeError(f"branch '{self.record.branch_id}' step failed: {outcome.error}")
        self.store.commit()
        return outcome

    def read(self, namespace: StateNamespace):
        return self.store.read(namespace)


def fork(
    checkpoint: Checkpoint,
    *,
    registry: NamespaceRegistry,
    branch_name: str = "branch",
    random_mode: str = "deterministic",
    parent_branch_id: str | None = None,
    pinned: bool = False,
    id_gen: IdGenerator | None = None,
) -> LifeBranch:
    """从 Checkpoint Fork 一个新 Branch（§21.6）。"""
    if random_mode not in RANDOM_MODES:
        raise ValueError(f"random_mode must be one of {RANDOM_MODES}")
    ids = id_gen or IdGenerator("BR", width=None)
    record = BranchRecord(
        branch_id=ids.next(),
        parent_branch_id=parent_branch_id,
        fork_checkpoint_id=checkpoint.checkpoint_id,
        fork_world_time=checkpoint.fork_world_time,
        created_at=checkpoint.fork_world_time,
        branch_name=branch_name,
        description="",
        random_mode=random_mode,
        pinned=pinned,
    )
    return LifeBranch(record, checkpoint, registry)
