"""P10 Branch 测试（§21：Fork 共享 pre-fork 历史，post-fork 独立演化）。"""

from datetime import datetime

import pytest

from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.plugins.default_life import register_default_life
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.emotion import INFLUENCE_TRIGGER, EmotionState
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.runtime.branch import fork
from animaflux.runtime.lifeloop import LifeRuntime


def _base() -> LifeRuntime:
    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())
    return runtime


def _joy(iid: str, valence: float) -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="emotion",
        influence_type=INFLUENCE_TRIGGER, magnitude=0.7, created_at=datetime(2000, 1, 1, 1),
        metadata={"emotion_type": "joy", "valence": valence, "arousal": 0.6},
    )


def test_branches_evolve_independently():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    a = fork(checkpoint, registry=runtime.registry, branch_name="A")
    b = fork(checkpoint, registry=runtime.registry, branch_name="B")

    a.step([_joy("A-1", 0.8)])
    b.step([_joy("B-1", -0.6)])

    assert a.read(StateNamespace.EMOTION).episodes[0].valence > 0
    assert b.read(StateNamespace.EMOTION).episodes[0].valence < 0
    assert a.read(StateNamespace.EMOTION) != b.read(StateNamespace.EMOTION)  # 互不污染（§21.8）


def test_branches_share_prefork_checkpoint():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    a = fork(checkpoint, registry=runtime.registry, branch_name="A")
    b = fork(checkpoint, registry=runtime.registry, branch_name="B")
    # pre-fork 共享：同一 fork checkpoint（§21.6 / §21.8）
    assert a.record.fork_checkpoint_id == checkpoint.checkpoint_id
    assert b.record.fork_checkpoint_id == checkpoint.checkpoint_id
    assert a.checkpoint is checkpoint
    assert b.checkpoint is checkpoint


def test_branch_record_metadata_complete():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    b = fork(checkpoint, registry=runtime.registry, branch_name="exp", random_mode="fresh_random", pinned=True)
    rec = b.record
    assert rec.branch_id.startswith("BR-")
    assert rec.parent_branch_id is None
    assert rec.fork_world_time == checkpoint.fork_world_time
    assert rec.branch_name == "exp"
    assert rec.random_mode == "fresh_random"
    assert rec.pinned is True


def test_fork_rejects_unknown_random_mode():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    with pytest.raises(ValueError):
        fork(checkpoint, registry=runtime.registry, random_mode="quantum")
