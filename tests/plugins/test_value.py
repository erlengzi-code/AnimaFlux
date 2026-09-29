"""P9 Value Owner 测试（§13H：非概率分布 / Bounded / Evidence-driven / 三维分离）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.value import (
    INFLUENCE_DEVELOP,
    INFLUENCE_FORM,
    ValueOwner,
    ValueState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="value",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_values_not_a_probability_distribution():
    # 多个 Value 可同时很高，不归一化、不要求总和为 1（§13H.4 / §13H.22）
    owner = ValueOwner()
    state = owner.resolve(ValueState(), [
        _inf(INFLUENCE_FORM, {"value_type": "family", "importance": 0.9}, "V-1"),
        _inf(INFLUENCE_FORM, {"value_type": "achievement", "importance": 0.9}, "V-2"),
    ], None).next_state
    assert len(state.commitments) == 2
    assert sum(v.importance for v in state.commitments) > 1.0  # 未被归一化


def test_importance_commitment_stability_are_separate():
    owner = ValueOwner()
    state = owner.resolve(ValueState(), [
        _inf(INFLUENCE_FORM, {"value_type": "family", "importance": 0.7, "commitment": 0.3, "stability": 0.9}),
    ], None).next_state
    v = state.commitments[0]
    assert v.importance != v.commitment != v.stability  # 三个维度独立（§13H.3）


def test_develop_without_evidence_ignored():
    owner = ValueOwner()
    state = owner.resolve(ValueState(), [
        _inf(INFLUENCE_FORM, {"value_type": "security", "importance": 0.5}, "V-1"),
    ], None).next_state
    out = owner.resolve(state, [
        _inf(INFLUENCE_DEVELOP, {"value_id": "V-1", "importance_delta": 0.5}),
    ], None).next_state
    assert out == state  # 单次普通事件不直接改 Value（§13H.7）


def test_develop_is_bounded():
    owner = ValueOwner()
    state = owner.resolve(ValueState(), [
        _inf(INFLUENCE_FORM, {"value_type": "security", "importance": 0.5}, "V-1"),
    ], None).next_state
    out = owner.resolve(state, [
        _inf(INFLUENCE_DEVELOP, {"value_id": "V-1", "importance_delta": 0.5, "evidence_refs": ("EV-1",)}),
    ], None).next_state
    before = state.commitments[0].importance
    after = out.commitments[0].importance
    assert 0.0 < after - before <= 0.1  # bounded（§13H.17）
