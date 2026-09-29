"""P4 Persistence Backend 契约测试（§18.6 两后端同一语义；§16B.3 Copy-on-Write；§16B.5 Journal）。"""

import pytest

from animaflux.contracts.persistence import CommitRecord, StateVersionRecord
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.persistence.sqlite import SqliteBackend


@pytest.fixture(params=["inmemory", "sqlite"])
def backend(request):
    if request.param == "inmemory":
        b = InMemoryBackend()
    else:
        b = SqliteBackend(":memory:")
    yield b
    if request.param == "sqlite":
        b.close()


def _version(svid: str, rev: int, *, ns: str = "emotion", payload: dict | None = None) -> StateVersionRecord:
    return StateVersionRecord(
        state_version_id=svid, agent_id="a", namespace=ns,
        revision=rev, payload=payload or {"joy": rev / 10},
    )


def _seed(backend) -> None:
    backend.begin()
    backend.write_version(_version("emotion_v1", 1))
    backend.write_current("a", "emotion", "emotion_v1")
    backend.commit()


def test_copy_on_write_versions_not_overwritten(backend):
    _seed(backend)
    backend.begin()
    backend.write_version(_version("emotion_v2", 2))
    backend.write_current("a", "emotion", "emotion_v2")
    backend.commit()
    # 新版本生效，旧版本仍可读（append-only，§16B.3）
    assert backend.read_current("a", "emotion") == "emotion_v2"
    assert backend.read_version("emotion_v1").revision == 1
    assert backend.read_version("emotion_v2").revision == 2


def test_commit_journal_recorded(backend):
    _seed(backend)
    rec = CommitRecord(commit_id="C1", agent_id="a", tick_id="t1", version_map={"emotion": "emotion_v1"})
    backend.begin()
    backend.write_commit(rec)
    backend.commit()
    assert backend.read_commit("C1") == rec


def test_rollback_discards_pending_writes(backend):
    _seed(backend)
    backend.begin()
    backend.write_version(_version("emotion_v2", 2))
    backend.write_current("a", "emotion", "emotion_v2")
    backend.rollback()
    assert backend.read_current("a", "emotion") == "emotion_v1"
    assert backend.read_version("emotion_v2") is None


def test_write_outside_transaction_raises(backend):
    with pytest.raises(RuntimeError):
        backend.write_version(_version("emotion_x", 99))


def test_list_current_returns_namespace_map(backend):
    _seed(backend)
    assert backend.list_current("a") == {"emotion": "emotion_v1"}
    assert backend.list_current("other-agent") == {}
