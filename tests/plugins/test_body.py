"""P5 Body Owner 测试（§13B：homeostasis / damage / sleep / vital_status / validation）。"""

from datetime import datetime

import pytest

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.body import (
    INFLUENCE_PHYSICAL_DAMAGE,
    INFLUENCE_SLEEP,
    INFLUENCE_TIME_UPDATE,
    BodyOwner,
    BodyState,
    Homeostasis,
    validate,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, magnitude: float = 0.0, metadata: dict | None = None) -> Influence:
    return Influence(
        influence_id="INF-1",
        source_plugin="test",
        target_state="body",
        influence_type=influence_type,
        magnitude=magnitude,
        created_at=T0,
        metadata=metadata or {},
    )


def test_time_update_drains_energy_and_builds_fatigue_when_awake():
    owner = BodyOwner()
    state = BodyState()
    out = owner.resolve(state, [_inf(INFLUENCE_TIME_UPDATE, metadata={"delta_seconds": 3600.0})], None)
    assert out.next_state.homeostasis.energy < state.homeostasis.energy
    assert out.next_state.sleep.fatigue > state.sleep.fatigue


def test_physical_damage_reduces_health_and_raises_pain():
    owner = BodyOwner()
    state = BodyState()
    out = owner.resolve(state, [_inf(INFLUENCE_PHYSICAL_DAMAGE, magnitude=0.4)], None)
    assert out.next_state.health.general_health < 1.0
    assert out.next_state.health.pain_signal > 0.0


def test_sleep_recovers_fatigue():
    owner = BodyOwner()
    tired = owner.resolve(BodyState(), [_inf(INFLUENCE_TIME_UPDATE, metadata={"delta_seconds": 3600.0})], None).next_state
    rested = owner.resolve(tired, [_inf(INFLUENCE_SLEEP, magnitude=0.9, metadata={"duration_seconds": 8 * 3600.0})], None).next_state
    assert rested.sleep.fatigue < tired.sleep.fatigue


def test_vital_status_dead_when_health_zero():
    owner = BodyOwner()
    out = owner.resolve(BodyState(), [_inf(INFLUENCE_PHYSICAL_DAMAGE, magnitude=1.5)], None)
    assert out.next_state.health.general_health == 0.0
    assert out.next_state.vital_status == "DEAD"


def test_validate_rejects_out_of_range():
    state = BodyState(homeostasis=Homeostasis(energy=1.5))
    with pytest.raises(ValueError):
        validate(state)
