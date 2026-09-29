"""P9 Personality Owner 测试（§13C：Bounded Change / Evidence-driven / Bias 非命令）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.personality import (
    INFLUENCE_DEVELOP,
    INFLUENCE_SET,
    PersonalityOwner,
    PersonalityState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="personality",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def _with_traits() -> PersonalityState:
    return PersonalityOwner().resolve(PersonalityState(), [
        _inf(INFLUENCE_SET, {"traits": {"openness": 0.5, "agreeableness": 0.5}}),
    ], None).next_state


def test_develop_without_evidence_ignored():
    # 普通事件不能直接改 Trait；无 Development Evidence → 不变（§13C.7）
    owner = PersonalityOwner()
    state = _with_traits()
    out = owner.resolve(state, [
        _inf(INFLUENCE_DEVELOP, {"trait": "openness", "delta": 0.5}),
    ], None).next_state
    assert out == state


def test_develop_is_bounded():
    # 单次步长 = clamp(delta, ±0.1) × plasticity；大 delta 被截断（§13C.13）
    owner = PersonalityOwner()
    state = _with_traits()
    out = owner.resolve(state, [
        _inf(INFLUENCE_DEVELOP, {"trait": "openness", "delta": 0.5, "evidence_refs": ("EV-1",)}),
    ], None).next_state
    before = next(t.value for t in state.traits if t.name == "openness")
    after = next(t.value for t in out.traits if t.name == "openness")
    assert abs(after - before) <= 0.1  # bounded（§13C.13）
    assert after > before  # 且确实按塑性向前移动


def test_personality_is_bias_not_command():
    # Personality 只有 Trait 倾向，没有 action/command 字段（§13C.15.2）
    state = _with_traits()
    assert not hasattr(state, "action")
    assert not hasattr(state, "command")
    assert not hasattr(state, "decision")


def test_trust_is_relationship_not_personality():
    # 对具体人物的 trust 属于 Relationship，不在 Personality Trait 里（§13C.5）
    state = _with_traits()
    assert all(t.name != "trust" for t in state.traits)


def test_set_clamps_to_range():
    owner = PersonalityOwner()
    out = owner.resolve(PersonalityState(), [
        _inf(INFLUENCE_SET, {"traits": {"openness": 1.5, "agreeableness": -0.5}}),
    ], None).next_state
    values = {t.name: t.value for t in out.traits}
    assert values["openness"] == 1.0
    assert values["agreeableness"] == 0.0
