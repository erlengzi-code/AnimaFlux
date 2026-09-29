"""Persistence 契约（v5.9 §17/§18/§19/§16B）。

State Persistence 分层：Hot State（Current Pointer）+ State Version（不可变）+ Commit Journal。
StateVersion 一经创建不可修改（§16B.1）；Current Pointer 独立存在、Commit 后段再更新（§19.8）；
Commit Journal 记录每个成功 Tick 的版本地图（§16.5）。Runtime 只依赖本契约，不依赖 SQLite（§18.4）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class StateVersionRecord:
    """不可变 State Version 的持久化记录（§16B.1）。payload 为 JSON 可序列化。"""

    state_version_id: str
    agent_id: str
    namespace: str
    revision: int
    payload: dict[str, Any]
    parent_version_id: str | None = None
    created_tick_id: str | None = None


@dataclass(frozen=True)
class CommitRecord:
    """Commit Journal 记录（§16B.5）：version_map = namespace → state_version_id。"""

    commit_id: str
    agent_id: str
    tick_id: str
    version_map: dict[str, str]
    runtime_time_after: str | None = None
    status: str = "COMMITTED"


class PersistenceBackend(Protocol):
    """持久化后端契约（§18.3 InMemory 与 §18.2 SQLite 遵守同一套语义）。"""

    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...

    def write_version(self, rec: StateVersionRecord) -> None: ...
    def write_commit(self, rec: CommitRecord) -> None: ...
    def write_current(self, agent_id: str, namespace: str, state_version_id: str) -> None: ...

    def read_version(self, state_version_id: str) -> StateVersionRecord | None: ...
    def read_current(self, agent_id: str, namespace: str) -> str | None: ...
    def read_commit(self, commit_id: str) -> CommitRecord | None: ...
    def list_current(self, agent_id: str) -> dict[str, str]: ...
    def list_commits(self, agent_id: str) -> list[CommitRecord]: ...
    def list_agents(self) -> list[str]: ...
    def delete_agent(self, agent_id: str) -> None: ...
