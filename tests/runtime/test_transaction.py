"""P4 Transaction Coordinator 测试（§19 Tick Transaction / §16D.14 Failure Injection）。"""

import pytest

from animaflux.contracts.persistence import StateVersionRecord
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.persistence.sqlite import SqliteBackend
from animaflux.runtime.transaction import TickCommitError, TransactionCoordinator


def _version(svid: str, rev: int, *, parent: str | None = None) -> StateVersionRecord:
    return StateVersionRecord(
        state_version_id=svid, agent_id="a", namespace="emotion",
        revision=rev, payload={"joy": rev / 10}, parent_version_id=parent,
    )


def test_commit_tick_persists_versions_journal_pointer():
    backend = InMemoryBackend()
    tc = TransactionCoordinator(backend)
    tc.commit_tick(
        agent_id="a", tick_id="t1", commit_id="C1",
        new_versions=[_version("emotion_v1", 1)],
        version_map={"emotion": "emotion_v1"},
    )
    assert backend.read_current("a", "emotion") == "emotion_v1"
    assert backend.read_version("emotion_v1").revision == 1
    assert backend.read_commit("C1").tick_id == "t1"
    assert backend.list_current("a") == {"emotion": "emotion_v1"}


def test_commit_tick_rolls_back_on_partial_failure():
    class FailOnCurrent:
        """注入 current pointer 发布失败（§16D.14）。"""

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def write_current(self, *args, **kwargs):
            raise RuntimeError("current pointer publish failure")

    backend = InMemoryBackend()
    TransactionCoordinator(backend).commit_tick(
        agent_id="a", tick_id="t1", commit_id="C1",
        new_versions=[_version("emotion_v1", 1)],
        version_map={"emotion": "emotion_v1"},
    )

    failing = TransactionCoordinator(FailOnCurrent(backend))
    with pytest.raises(TickCommitError):
        failing.commit_tick(
            agent_id="a", tick_id="t2", commit_id="C2",
            new_versions=[_version("emotion_v2", 2, parent="emotion_v1")],
            version_map={"emotion": "emotion_v2"},
        )
    # 半提交状态不得存在：v2 被回滚，旧指针仍是权威（§19.10）
    assert backend.read_current("a", "emotion") == "emotion_v1"
    assert backend.read_version("emotion_v2") is None
    assert backend.read_commit("C2") is None


def test_commit_tick_works_with_sqlite_backend():
    backend = SqliteBackend(":memory:")
    try:
        tc = TransactionCoordinator(backend)
        tc.commit_tick(
            agent_id="a", tick_id="t1", commit_id="C1",
            new_versions=[_version("emotion_v1", 1)],
            version_map={"emotion": "emotion_v1"},
        )
        assert backend.read_current("a", "emotion") == "emotion_v1"
        assert backend.read_version("emotion_v1").revision == 1
    finally:
        backend.close()
