"""P6 Perception 测试（§14A：Sensory Gate / Attention / Interpretation / Misperception）。"""

from datetime import datetime

from animaflux.contracts.environment import Observation, ObservationBatch
from animaflux.plugins.default_cognition.perception import PerceptionProcess

T0 = datetime(2000, 1, 1)


def _obs(oid, modality="visual", content="x", clarity=1.0, noise=0.0, intensity=0.5, source=None):
    return Observation(
        observation_id=oid, modality=modality, content=content, world_time=T0,
        source_entity=source, clarity=clarity, noise=noise, intensity=intensity,
    )


def _perceive(observations, *, sensory=None, budget=5):
    batch = ObservationBatch(observations=tuple(observations), world_time=T0)
    return PerceptionProcess(attention_budget=budget).perceive(batch, None, sensory_capabilities=sensory)


def test_sensory_gate_drops_visual_when_blind():
    result = _perceive([_obs("o1", modality="visual", content="a red ball", clarity=0.9)], sensory={"vision": 0.0})
    assert result.perceived_events == ()
    assert result.dropped_observation_refs == ("o1",)


def test_attention_budget_keeps_highest_salience():
    obs = [_obs("o1", intensity=0.9), _obs("o2", intensity=0.8), _obs("o3", intensity=0.1)]
    result = _perceive(obs, budget=2)
    kept = {e.source_observation_refs[0] for e in result.perceived_events}
    assert kept == {"o1", "o2"}
    assert "o3" in result.dropped_observation_refs


def test_high_clarity_no_misperception():
    result = _perceive([_obs("o1", clarity=0.9, content="hello")])
    pe = result.perceived_events[0]
    assert pe.misperception is False
    assert pe.confidence == 0.9
    assert pe.perceived_content == "hello"


def test_low_clarity_misperception_has_mechanism_source():
    result = _perceive([_obs("o1", clarity=0.3, content="hello")])
    pe = result.perceived_events[0]
    assert pe.misperception is True
    assert pe.misperception_cause == "low_clarity"
    assert pe.perceived_content == "~hello~"


def test_high_noise_misperception():
    result = _perceive([_obs("o1", clarity=0.9, noise=0.8, content="hello")])
    pe = result.perceived_events[0]
    assert pe.misperception is True
    assert pe.misperception_cause == "noise"


def test_perceived_event_carries_uncertainty_downstream():
    result = _perceive([_obs("o1", clarity=0.5, noise=0.0, content="maybe", source="B")])
    pe = result.perceived_events[0]
    assert pe.uncertainty == 0.5
    assert pe.entity_refs == ("B",)
