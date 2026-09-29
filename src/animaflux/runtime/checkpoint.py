"""Checkpoint（v5.9 §15 / §20 / §21.6）。

Checkpoint = 长期一致性恢复点，也是 Life Branch 的 Fork 点（§21.6）。它快照某一时刻的
State Version Map + 各 Namespace 的不可变状态对象 + Environment Fingerprint（§22.13）。
Fork 前 State Version 可共享（§21.8）：Checkpoint 里的 state 对象是 frozen 不可变快照，
Branch 直接共享引用，不复制、不重写历史。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from animaflux.kernel.ids import IdGenerator


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    agent_id: str
    fork_world_time: str
    version_map: dict[str, str]          # namespace -> durable state_version_id（pre-fork 权威版本）
    states: dict[str, Any]               # namespace -> 不可变状态对象（供 in-memory Fork 共享引用）
    environment_fingerprint: dict[str, Any]


def capture_checkpoint(
    *,
    agent_id: str,
    world_time: datetime,
    version_map: dict[str, str],
    states: dict[str, Any],
    fingerprint: dict[str, Any] | None = None,
    checkpoint_id: str | None = None,
    id_gen: IdGenerator | None = None,
) -> Checkpoint:
    """从当前 Runtime 的版本地图 + 状态快照构造一个 Checkpoint（§15.11 / §21.6）。"""
    ids = id_gen or IdGenerator("CKPT", width=None)
    return Checkpoint(
        checkpoint_id=checkpoint_id or ids.next(),
        agent_id=agent_id,
        fork_world_time=world_time.isoformat(),
        version_map=dict(version_map),
        states=dict(states),
        environment_fingerprint=dict(fingerprint or {}),
    )
