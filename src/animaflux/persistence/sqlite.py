"""SQLite Persistence Backend（v5.9 §18.2，v0.1 默认正式后端）。

第一批表（§16B.44）：state_version / state_current / commit_journal。
StateVersion 不可变、append-only（§16B.1）；Current Pointer 独立、可 replace（§16B.2）。
一次 Tick Critical Commit 用一个 SQLite Transaction 保证原子性（§16B.36 / §19.10）。

线程模型（Web Plan §6 / §9 / §40 第 2 条）：
  Web 的 FastAPI 同步路由跑在 threadpool 线程上，连接对象会跨线程使用。因此这里：
    - `check_same_thread=False`：允许连接被 worker 线程复用（真实编码证明的冲突，§40）；
    - `PRAGMA journal_mode=WAL`：读多写少的本地部署（§6 原本即要求 WAL）；
    - 实例级 `RLock` 串行化对单一连接的访问；事务锁从 `begin()` 持有到 `commit()`/`rollback()`
      释放，保证一次 Critical Commit 不被其他线程穿插。
  这是后端自身的线程安全边界；Web 层仍按 (agent_id, branch_id) 锁做单写者（§8）。
"""

from __future__ import annotations

import json
import sqlite3
import threading

from animaflux.contracts.persistence import CommitRecord, StateVersionRecord


_SCHEMA = """
CREATE TABLE IF NOT EXISTS state_version (
    state_version_id TEXT PRIMARY KEY,
    agent_id       TEXT NOT NULL,
    namespace      TEXT NOT NULL,
    revision       INTEGER NOT NULL,
    payload_json   TEXT NOT NULL,
    parent_version_id TEXT,
    created_tick_id   TEXT
);
CREATE TABLE IF NOT EXISTS state_current (
    agent_id        TEXT NOT NULL,
    namespace       TEXT NOT NULL,
    state_version_id TEXT NOT NULL,
    PRIMARY KEY (agent_id, namespace)
);
CREATE TABLE IF NOT EXISTS commit_journal (
    commit_id        TEXT PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    tick_id          TEXT NOT NULL,
    status           TEXT NOT NULL,
    version_map_json TEXT NOT NULL,
    runtime_time_after TEXT
);
"""


class SqliteBackend:
    """SQLite 后端；显式 BEGIN/COMMIT/ROLLBACK 管理事务（isolation_level=None 关闭隐式事务）。"""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._in_tx = False
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- 事务 --
    def begin(self) -> None:
        self._lock.acquire()
        if self._in_tx:
            self._lock.release()
            raise RuntimeError("transaction already active")
        try:
            self._conn.execute("BEGIN")
            self._in_tx = True
        except BaseException:
            self._in_tx = False
            self._lock.release()
            raise

    def commit(self) -> None:
        if not self._in_tx:
            raise RuntimeError("no active transaction")
        try:
            self._conn.execute("COMMIT")
        finally:
            self._in_tx = False
            self._lock.release()

    def rollback(self) -> None:
        if not self._in_tx:
            raise RuntimeError("no active transaction")
        try:
            self._conn.execute("ROLLBACK")
        finally:
            self._in_tx = False
            self._lock.release()

    # -- 写（须在事务内，锁已由 begin() 持有） --
    def write_version(self, rec: StateVersionRecord) -> None:
        self._require_tx()
        self._conn.execute(
            "INSERT INTO state_version VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rec.state_version_id, rec.agent_id, rec.namespace, rec.revision,
             json.dumps(rec.payload), rec.parent_version_id, rec.created_tick_id),
        )

    def write_commit(self, rec: CommitRecord) -> None:
        self._require_tx()
        self._conn.execute(
            "INSERT INTO commit_journal VALUES (?, ?, ?, ?, ?, ?)",
            (rec.commit_id, rec.agent_id, rec.tick_id, rec.status,
             json.dumps(rec.version_map), rec.runtime_time_after),
        )

    def write_current(self, agent_id: str, namespace: str, state_version_id: str) -> None:
        self._require_tx()
        self._conn.execute(
            "INSERT OR REPLACE INTO state_current VALUES (?, ?, ?)",
            (agent_id, namespace, state_version_id),
        )

    # -- 读 --
    def read_version(self, state_version_id: str) -> StateVersionRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_version_id, agent_id, namespace, revision, payload_json, "
                "parent_version_id, created_tick_id FROM state_version WHERE state_version_id = ?",
                (state_version_id,),
            ).fetchone()
        if row is None:
            return None
        return StateVersionRecord(
            state_version_id=row[0], agent_id=row[1], namespace=row[2], revision=row[3],
            payload=json.loads(row[4]), parent_version_id=row[5], created_tick_id=row[6],
        )

    def read_current(self, agent_id: str, namespace: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT state_version_id FROM state_current WHERE agent_id = ? AND namespace = ?",
                (agent_id, namespace),
            ).fetchone()
        return row[0] if row else None

    def read_commit(self, commit_id: str) -> CommitRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT commit_id, agent_id, tick_id, status, version_map_json, runtime_time_after "
                "FROM commit_journal WHERE commit_id = ?",
                (commit_id,),
            ).fetchone()
        if row is None:
            return None
        return CommitRecord(
            commit_id=row[0], agent_id=row[1], tick_id=row[2], status=row[3],
            version_map=json.loads(row[4]), runtime_time_after=row[5],
        )

    def list_current(self, agent_id: str) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT namespace, state_version_id FROM state_current WHERE agent_id = ?",
                (agent_id,),
            ).fetchall()
        return {namespace: state_version_id for namespace, state_version_id in rows}

    def list_commits(self, agent_id: str) -> list[CommitRecord]:
        # rowid 顺序 = 插入顺序 = Commit Journal 顺序（§16B.5）
        with self._lock:
            rows = self._conn.execute(
                "SELECT commit_id, agent_id, tick_id, status, version_map_json, runtime_time_after "
                "FROM commit_journal WHERE agent_id = ? ORDER BY rowid",
                (agent_id,),
            ).fetchall()
        return [
            CommitRecord(
                commit_id=r[0], agent_id=r[1], tick_id=r[2], status=r[3],
                version_map=json.loads(r[4]), runtime_time_after=r[5],
            )
            for r in rows
        ]

    def list_agents(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT agent_id FROM state_current ORDER BY agent_id"
            ).fetchall()
        return [r[0] for r in rows]

    def delete_agent(self, agent_id: str) -> None:
        """永久删除一条生命（§Web Plan §10）：原子移除其 state_version / state_current /
        commit_journal。不可逆，由 Web 层在确认后调用。"""
        self.begin()
        try:
            self._conn.execute("DELETE FROM state_version WHERE agent_id = ?", (agent_id,))
            self._conn.execute("DELETE FROM state_current WHERE agent_id = ?", (agent_id,))
            self._conn.execute("DELETE FROM commit_journal WHERE agent_id = ?", (agent_id,))
        except BaseException:
            self.rollback()
            raise
        self.commit()

    def _require_tx(self) -> None:
        if not self._in_tx:
            raise RuntimeError("write outside transaction")
