"""P5 Emotion Owner 测试（§13D：多情绪共存 / decay / mood）。"""

from datetime import datetime

import pytest

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.emotion import (
    INFLUENCE_DECAY,
    INFLUENCE_TRIGGER,
    EmotionEpisode,
    EmotionOwner,
    EmotionState,
    validate,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, magnitude: float = 0.0, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid,
        source_plugin="test",
        target_state="emotion",
        influence_type=influence_type,
        magnitude=magnitude,
        created_at=T0,
        metadata=metadata or {},
    )


def test_trigger_adds_episodes_multiple_coexist():
    owner = EmotionOwner()
    out = owner.resolve(EmotionState(), [
        _inf(INFLUENCE_TRIGGER, 0.6, {"emotion_type": "sadness", "valence": -0.5, "arousal": 0.4}, iid="INF-1"),
        _inf(INFLUENCE_TRIGGER, 0.4, {"emotion_type": "relief", "valence": 0.5, "arousal": 0.3}, iid="INF-2"),
    ], None)
    assert {e.emotion_type for e in out.next_state.episodes} == {"sadness", "relief"}


def test_decay_reduces_intensity():
    owner = EmotionOwner()
    triggered = owner.resolve(
        EmotionState(),
        [_inf(INFLUENCE_TRIGGER, 0.8, {"emotion_type": "anger", "valence": -0.4, "arousal": 0.7})],
        None,
    ).next_state
    decayed = owner.resolve(triggered, [_inf(INFLUENCE_DECAY, metadata={"delta_seconds": 18000.0})], None).next_state
    assert decayed.episodes[0].intensity < 0.8


def test_mood_pulls_toward_episode_valence():
    owner = EmotionOwner()
    out = owner.resolve(
        EmotionState(),
        [_inf(INFLUENCE_TRIGGER, 0.9, {"emotion_type": "joy", "valence": 0.9, "arousal": 0.6})],
        None,
    )
    assert out.next_state.mood.valence > 0.0


def test_validate_rejects_bad_valence():
    state = EmotionState(episodes=(
        EmotionEpisode(episode_id="e1", emotion_type="joy", intensity=0.5, valence=2.0, arousal=0.5, started_at=T0, last_updated_at=T0),
    ))
    with pytest.raises(ValueError):
        validate(state)
