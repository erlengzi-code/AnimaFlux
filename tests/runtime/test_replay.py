"""P10 Replay 测试（§21 / §22.9：Read-only 回放 / 不重拨 LLM / 结果与历史一致）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.plugins.default_life import register_default_life
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.emotion import INFLUENCE_TRIGGER, EmotionState
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.runtime.lifeloop import LifeRuntime
from animaflux.runtime.replay import ReplayEngine


def _build_life() -> LifeRuntime:
    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())
    return runtime


def test_replay_is_read_only_and_never_calls_llm():
    life = _build_life()
    life.step(3600.0)
    life.step(3600.0)

    backend = life.backend
    versions_before = set(backend._versions.keys())
    commits_before = set(backend._commits.keys())

    engine = ReplayEngine(backend)
    ticks = engine.replay_timeline("agent-1")

    assert engine.llm_calls == 0   # 永不回拨 LLM（§22.9）
    assert engine.write_ops == 0   # 只读，无写入（§21.3）
    assert set(backend._versions.keys()) == versions_before  # 无新 State Version（§21.2）
    assert set(backend._commits.keys()) == commits_before
    assert len(ticks) == 5  # 3 个 seed commit + 2 个 step commit


def test_replay_reconstructs_exact_history_payload():
    from animaflux.plugins.default_life.emotion import serialize as emotion_serialize

    life = _build_life()
    trigger = Influence(
        influence_id="EXT-1", source_plugin="test", target_state="emotion",
        influence_type=INFLUENCE_TRIGGER, magnitude=0.7, created_at=life.now(),
        metadata={"emotion_type": "joy", "valence": 0.8, "arousal": 0.6},
    )
    life.step(60.0, extra_influences=(trigger,))
    life.step(60.0)

    engine = ReplayEngine(life.backend)
    ticks = engine.replay_timeline("agent-1")

    # 最后一条 emotion 回放 payload 与当前 serialized 状态完全一致（§16D.17）
    current = emotion_serialize(life.read(StateNamespace.EMOTION))
    emotion_ticks = [t for t in ticks if "emotion" in t.payloads and t.tick_id != "t0"]
    assert emotion_ticks[-1].payloads["emotion"] == current
