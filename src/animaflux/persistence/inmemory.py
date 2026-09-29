"""InMemory Persistence Backend（v5.9 §18.3）。

用于单元测试 / Runtime 测试 / 快速实验，与 SQLite 遵守同一套 Store Contract 与事务语义
（§18.6），但不是长期 Source of Truth。
"""

from __future__ import annotations

from animaflux.contracts.persistence import CommitRecord, StateVersionRecord


class InMemoryBackend:
    """字典实现的持久化后端；写只能在事务内，commit 才真正生效，rollback 丢弃 pending。"""

    def __init__(self) -> None:
        self._versions: dict[str, StateVersionRecord] = {}
        self._current: dict[tuple[str, str], str] = {}
        self._commits: dict[str, CommitRecord] = {}
        self._pending: list[tuple[str, tuple]] | None = None

    # -- 事务 --
    def begin(self) -> None:
        if self._pending is not None:
            raise RuntimeError("transaction already active")
        self._pending = []

    def commit(self) -> None:
        pending = self._pending
        if pending is None:
            raise RuntimeError("no active transaction")
        for op, args in pending:
            self._apply(op, args)
        self._pending = None

    def rollback(self) -> None:
        self._pending = None

    # -- 写（须在事务内） --
    def write_version(self, rec: StateVersionRecord) -> None:
        self._record("write_version", rec)

    def write_commit(self, rec: CommitRecord) -> None:
        self._record("write_commit", rec)

    def write_current(self, agent_id: str, namespace: str, state_version_id: str) -> None:
        self._record("write_current", agent_id, namespace, state_version_id)

    # -- 读 --
    def read_version(self, state_version_id: str) -> StateVersionRecord | None:
        return self._versions.get(state_version_id)

    def read_current(self, agent_id: str, namespace: str) -> str | None:
        return self._current.get((agent_id, namespace))

    def read_commit(self, commit_id: str) -> CommitRecord | None:
        return self._commits.get(commit_id)

    def list_current(self, agent_id: str) -> dict[str, str]:
        return {ns: vid for (aid, ns), vid in self._current.items() if aid == agent_id}

    def list_commits(self, agent_id: str) -> list[CommitRecord]:
        # dict 保持插入顺序 = Commit Journal 顺序（§16B.5）
        return [c for c in self._commits.values() if c.agent_id == agent_id]

    def list_agents(self) -> list[str]:
        return sorted({aid for (aid, _ns) in self._current.keys()})

    def delete_agent(self, agent_id: str) -> None:
        """永久删除一条生命：移除其 versions / current / commits（与 SQLite 同语义）。"""
        self._versions = {vid: rec for vid, rec in self._versions.items() if rec.agent_id != agent_id}
        self._current = {k: v for k, v in self._current.items() if k[0] != agent_id}
        self._commits = {cid: rec for cid, rec in self._commits.items() if rec.agent_id != agent_id}

    # -- 内部 --
    def _record(self, op: str, *args) -> None:
        if self._pending is None:
            raise RuntimeError("write outside transaction")
        self._pending.append((op, args))

    def _apply(self, op: str, args: tuple) -> None:
        if op == "write_version":
            rec = args[0]
            self._versions[rec.state_version_id] = rec
        elif op == "write_commit":
            rec = args[0]
            self._commits[rec.commit_id] = rec
        elif op == "write_current":
            agent_id, namespace, state_version_id = args
            self._current[(agent_id, namespace)] = state_version_id
        else:
            raise AssertionError(f"unknown op '{op}'")
