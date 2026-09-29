"""P3 State Store 测试（§14 三类版本 / §15 Copy-on-Write / Commit-Rollback）。"""

from dataclasses import dataclass

import pytest

from animaflux.contracts.state import StateNamespace
from animaflux.kernel.registry import NamespaceRegistry
from animaflux.state.state_store import StateStore

EMOTION = StateNamespace.EMOTION
BODY = StateNamespace.BODY


@dataclass(frozen=True)
class EmotionState:
    joy: float = 0.5
    sadness: float = 0.0


def test_seed_and_read_committed():
    store = StateStore("agent-1")
    v = store.seed(EMOTION, EmotionState(joy=0.5))
    assert v.version == 1
    assert store.read(EMOTION) == EmotionState(joy=0.5)


def test_snapshot_reads_stable_view():
    store = StateStore("agent-1")
    store.seed(EMOTION, EmotionState(joy=0.5))
    store.begin_tick()
    assert store.read(EMOTION) == EmotionState(joy=0.5)


def test_stage_copy_on_write_new_version():
    store = StateStore("agent-1")
    store.seed(EMOTION, EmotionState(joy=0.5))
    store.begin_tick()
    staged = store.stage(EMOTION, EmotionState(joy=0.8), owner=None)
    assert staged.version == 2
    assert store.read(EMOTION).joy == 0.8
    # Working 已变，Committed 仍是 v1
    assert store.committed_version(EMOTION).version == 1


def test_unchanged_namespace_keeps_version_ref():
    store = StateStore("agent-1")
    store.seed(EMOTION, EmotionState(joy=0.5))
    store.seed(BODY, {"energy": 1.0})
    store.begin_tick()
    v = store.stage(EMOTION, EmotionState(joy=0.8), owner=None)
    store.commit()
    # 只有 emotion 出了新版本，body 复用旧版本引用（§15.4）
    assert store.committed_version(EMOTION) == v
    assert store.committed_version(EMOTION).version == 2
    assert store.committed_version(BODY).version == 1


def test_commit_promotes_working():
    store = StateStore("agent-1")
    store.seed(EMOTION, EmotionState())
    store.begin_tick()
    store.stage(EMOTION, EmotionState(joy=1.0), owner=None)
    store.commit()
    assert store.read(EMOTION).joy == 1.0
    assert store.committed_version(EMOTION).version == 2


def test_rollback_discards_working():
    store = StateStore("agent-1")
    store.seed(EMOTION, EmotionState(joy=0.5))
    store.begin_tick()
    store.stage(EMOTION, EmotionState(joy=0.9), owner=None)
    store.rollback()
    assert store.read(EMOTION).joy == 0.5
    assert store.committed_version(EMOTION).version == 1


def test_stage_non_owner_rejected():
    registry = NamespaceRegistry()
    store = StateStore("agent-1", registry)
    store.seed(EMOTION, EmotionState())
    owner = object()
    other = object()
    registry.register_owner(EMOTION, owner)
    store.begin_tick()
    with pytest.raises(PermissionError):
        store.stage(EMOTION, EmotionState(joy=0.9), owner=other)


def test_stage_owner_allowed():
    registry = NamespaceRegistry()
    store = StateStore("agent-1", registry)
    store.seed(EMOTION, EmotionState())
    owner = object()
    registry.register_owner(EMOTION, owner)
    store.begin_tick()
    v = store.stage(EMOTION, EmotionState(joy=0.9), owner=owner)
    assert v.version == 2
