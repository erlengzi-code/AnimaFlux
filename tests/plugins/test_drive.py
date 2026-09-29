"""P8 Drive Owner 测试（§13E：Need/Drive 分离 / 惯性 / 多 Need 共存）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.drive import (
    INFLUENCE_ACTIVATE,
    INFLUENCE_NEED_ASSESS,
    INFLUENCE_SATISFY,
    DriveOwner,
    DriveState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="drive",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_need_and_drive_separate():
    owner = DriveOwner()
    state = owner.resolve(DriveState(), [
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "belonging", "intensity": 0.7, "satisfaction": 0.3}, "N-1"),
        _inf(INFLUENCE_ACTIVATE, {"drive_type": "affiliation", "activation": 0.6, "source_need_refs": ("N-1",)}, "D-1"),
    ], None).next_state
    assert [n.need_type for n in state.needs] == ["belonging"]  # Need 在 needs
    assert [d.drive_type for d in state.active_drives] == ["affiliation"]  # Drive 在 active_drives
    assert state.active_drives[0].source_need_refs == ("N-1",)


def test_multiple_needs_coexist():
    owner = DriveOwner()
    state = owner.resolve(DriveState(), [
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "hunger", "intensity": 0.8}, "N-1"),
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "belonging", "intensity": 0.6}, "N-2"),
    ], None).next_state
    assert {n.need_type for n in state.needs} == {"hunger", "belonging"}


def test_satisfaction_does_not_zero_need_instantly():
    owner = DriveOwner()
    assessed = owner.resolve(DriveState(), [
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "belonging", "intensity": 0.8, "satisfaction": 0.2}),
    ], None).next_state
    satisfied = owner.resolve(assessed, [
        _inf(INFLUENCE_SATISFY, {"need_type": "belonging", "amount": 0.3}),
    ], None).next_state
    need = satisfied.needs[0]
    assert need.satisfaction > 0.2  # 满足提升
    assert need.intensity > 0.0     # 惯性：不瞬间归零（§13E.10）
    assert need.intensity < 0.8     # 但确在下降


def test_need_assessment_is_inertial():
    owner = DriveOwner()
    first = owner.resolve(DriveState(), [
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "hunger", "intensity": 0.5, "satisfaction": 0.5}),
    ], None).next_state
    # 第二次评估向 0.9 靠拢，但因惯性不会一步到位（§13E.10）
    second = owner.resolve(first, [
        _inf(INFLUENCE_NEED_ASSESS, {"need_type": "hunger", "intensity": 0.9, "satisfaction": 0.1}),
    ], None).next_state
    need = second.needs[0]
    assert 0.5 < need.intensity < 0.9
