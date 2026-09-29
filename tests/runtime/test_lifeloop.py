"""P5 LifeRuntime 测试（§16.2 每个成功 Tick Durable Commit / step/advance）。"""

from datetime import datetime

from animaflux.contracts.environment import Observation
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.plugins.default_life import register_default_life
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.emotion import EmotionState, INFLUENCE_TRIGGER
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.runtime.lifeloop import LifeRuntime


def _build_life() -> LifeRuntime:
    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())
    return runtime


def test_seed_and_step_advance_time():
    life = _build_life()
    assert life.now() == datetime(2000, 1, 1)
    life.step(3600.0)
    assert life.now() == datetime(2000, 1, 1, 1, 0, 0)


def test_step_evolves_body_homeostasis():
    life = _build_life()
    energy_before = life.read(StateNamespace.BODY).homeostasis.energy
    life.step(3600.0)
    energy_after = life.read(StateNamespace.BODY).homeostasis.energy
    assert energy_after < energy_before


def test_step_durably_commits_changed_namespace():
    life = _build_life()
    life.step(3600.0)
    assert life.store.committed_version(StateNamespace.BODY).version == 2
    assert life.backend.read_current("agent-1", "body") == "agent-1:body_v2"
    assert life.backend.read_version("agent-1:body_v2") is not None


def test_step_with_emotion_trigger_commits_emotion():
    life = _build_life()
    trigger = Influence(
        influence_id="EXT-1",
        source_plugin="test",
        target_state="emotion",
        influence_type=INFLUENCE_TRIGGER,
        magnitude=0.7,
        created_at=life.now(),
        metadata={"emotion_type": "joy", "valence": 0.8, "arousal": 0.6},
    )
    life.step(60.0, extra_influences=(trigger,))
    emotion = life.read(StateNamespace.EMOTION)
    assert any(e.emotion_type == "joy" for e in emotion.episodes)
    assert life.backend.read_current("agent-1", "emotion") == "agent-1:emotion_v2"


def test_observation_to_emotion_full_cognition_chain():
    # Objective Observation → Perception → Appraisal → Emotion Influence → Resolver → Emotion State
    life = _build_life()
    obs = Observation(
        observation_id="obs-1",
        modality="auditory",
        content="there is a threat approaching",
        world_time=life.now(),
        clarity=0.9,
        intensity=0.8,
        source_entity="guard",
        source_event_refs=("EVT-9",),
    )
    life.step(60.0, observations=(obs,))
    emotion = life.read(StateNamespace.EMOTION)
    assert any(e.emotion_type == "fear" for e in emotion.episodes)
    assert life.backend.read_current("agent-1", "emotion") == "agent-1:emotion_v2"
