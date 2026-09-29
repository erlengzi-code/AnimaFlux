"""Transaction Coordinator（v5.9 §19.2）。

编排一次 Tick 的 Critical Commit：按 §19.7 顺序——先 persist 新 State Version，再写 Commit
Journal，最后更新 Current State Pointer（§19.8）。任何一步失败 → rollback，不留半提交生命状态
（§19.10 / §16D.14）。Plugin 不直接管理数据库事务（§19.14）。
"""

from __future__ import annotations

from animaflux.contracts.persistence import CommitRecord, PersistenceBackend, StateVersionRecord


class TickCommitError(Exception):
    """一次 Tick Commit 失败（已 rollback）。"""


class TransactionCoordinator:
    def __init__(self, backend: PersistenceBackend) -> None:
        self._backend = backend

    def commit_tick(
        self,
        *,
        agent_id: str,
        tick_id: str,
        commit_id: str,
        new_versions: list[StateVersionRecord],
        version_map: dict[str, str],
        runtime_time_after: str | None = None,
    ) -> CommitRecord:
        """按 §19.7 顺序原子持久化一次 Tick 的关键写入。

        顺序：new state versions → commit journal → current pointers（最后，§19.8）。
        """
        commit_rec = CommitRecord(
            commit_id=commit_id,
            agent_id=agent_id,
            tick_id=tick_id,
            version_map=dict(version_map),
            runtime_time_after=runtime_time_after,
        )
        self._backend.begin()
        try:
            for rec in new_versions:
                self._backend.write_version(rec)
            self._backend.write_commit(commit_rec)
            for namespace, state_version_id in version_map.items():
                self._backend.write_current(agent_id, namespace, state_version_id)
        except Exception as exc:
            self._backend.rollback()
            raise TickCommitError(f"tick '{tick_id}' commit failed, rolled back: {exc}") from exc
        self._backend.commit()
        return commit_rec
