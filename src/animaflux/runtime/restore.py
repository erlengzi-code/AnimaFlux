"""RESTORE（v5.9 §21.1）：加载最新已提交状态并继续原 Runtime。

三种模式严格区分（§21.1）：
- RESTORE：加载已提交快照，在原 agent 上继续，不创建新 branch_id。
- REPLAY：只读回放历史（见 replay.py），不产生新状态。
- RESIMULATE-BRANCH：从 Checkpoint fork 新 Branch（见 branch.py）。
"""

from __future__ import annotations

from animaflux.contracts.state import StateNamespace
from animaflux.kernel.registry import NamespaceRegistry
from animaflux.runtime.checkpoint import Checkpoint
from animaflux.state.state_store import StateStore


def restore(checkpoint: Checkpoint, *, registry: NamespaceRegistry) -> StateStore:
    """以 Checkpoint 的已提交状态重建原 agent 的 StateStore，继续同一 Runtime（§21.1 RESTORE）。

    与 fork() 的区别：不产生 BranchRecord / branch_id，时间线仍在原 agent 上线性继续。
    """
    store = StateStore(checkpoint.agent_id, registry=registry)
    for ns_value, state in checkpoint.states.items():
        store.seed(StateNamespace(ns_value), state)
    return store
