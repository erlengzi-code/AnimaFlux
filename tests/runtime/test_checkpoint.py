"""P10 Checkpoint 测试（§15 / §20 / §21.6：版本地图 + 状态快照 + Fingerprint）。"""

from datetime import datetime

from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.plugins.default_life import register_default_life
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.emotion import EmotionState
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.runtime.lifeloop import LifeRuntime


def _build_life() -> LifeRuntime:
    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())
    return runtime


def test_checkpoint_captures_version_map_and_states():
    life = _build_life()
    life.step(3600.0)  # body 变化 → body_v2
    ckpt = life.checkpoint()
    assert ckpt.agent_id == "agent-1"
    assert ckpt.version_map["identity"] == "agent-1:identity_v1"
    assert ckpt.version_map["body"] == "agent-1:body_v2"
    assert ckpt.version_map["emotion"] == "agent-1:emotion_v1"
    assert StateNamespace.BODY.value in ckpt.states  # 状态快照含 body
    assert ckpt.fork_world_time == life.now().isoformat()


def test_checkpoint_immutable_states_are_shared_snapshot():
    life = _build_life()
    ckpt = life.checkpoint()
    # 状态快照是不可变对象，可直接共享（§21.8）
    assert ckpt.states["emotion"] == life.read(StateNamespace.EMOTION)


def test_checkpoint_fingerprint_records_random_seed():
    life = _build_life()
    ckpt = life.checkpoint()
    assert ckpt.environment_fingerprint["root_seed"] == life.random.root_seed
