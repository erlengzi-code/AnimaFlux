"""P8 Relationship Owner 测试（§13J：Directional / 多维 / 慢速维度不衰减）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.relationship import (
    INFLUENCE_DECAY,
    INFLUENCE_FORM,
    INFLUENCE_UPDATE,
    RelationshipOwner,
    RelationshipProfile,
    RelationshipState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="relationship",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_relationships_are_independent():
    owner = RelationshipOwner()
    state = owner.resolve(RelationshipState(), [
        _inf(INFLUENCE_FORM, {"target_id": "B", "dimensions": {"trust": 0.5}}, "R-1"),
        _inf(INFLUENCE_FORM, {"target_id": "C", "dimensions": {"trust": 0.1}}, "R-2"),
    ], None).next_state
    updated = owner.resolve(state, [
        _inf(INFLUENCE_UPDATE, {"target_id": "B", "dimension": "trust", "delta": 0.3}),
    ], None).next_state
    by_target = {r.target_id: r for r in updated.relationships}
    assert by_target["B"].dimensions.trust == 0.6  # 0.5 + 0.1（慢速维度 bounded，§13J.10）
    assert by_target["C"].dimensions.trust == 0.1  # B 的更新不影响 C（§13J.2）


def test_no_single_favorability():
    r = RelationshipProfile(target_id="B")
    assert not hasattr(r, "favorability")  # 禁止单一 favorability（§13J.3）
    assert hasattr(r.dimensions, "trust")
    assert hasattr(r.dimensions, "affection")
    assert hasattr(r.dimensions, "resentment")


def test_update_changes_only_target_dimension():
    owner = RelationshipOwner()
    state = owner.resolve(RelationshipState(), [
        _inf(INFLUENCE_FORM, {"target_id": "B", "dimensions": {"trust": 0.3, "affection": 0.3}}),
    ], None).next_state
    updated = owner.resolve(state, [
        _inf(INFLUENCE_UPDATE, {"target_id": "B", "dimension": "affection", "delta": 0.5}),
    ], None).next_state
    r = updated.relationships[0]
    assert r.dimensions.affection == 0.8  # 快速维度全量更新
    assert r.dimensions.trust == 0.3     # 其它维度不变（多维分离，§13J.3）


def test_decay_spares_slow_dimensions():
    owner = RelationshipOwner()
    state = owner.resolve(RelationshipState(), [
        _inf(INFLUENCE_FORM, {"target_id": "B", "dimensions": {
            "trust": 0.5, "attachment": 0.5, "closeness": 0.5, "resentment": 0.5,
        }}),
    ], None).next_state
    decayed = owner.resolve(state, [
        _inf(INFLUENCE_DECAY, {"target_id": "B", "delta_seconds": 86400.0}),
    ], None).next_state
    r = decayed.relationships[0]
    assert r.dimensions.closeness < 0.5  # 快速维度衰减
    assert r.dimensions.trust == 0.5     # 慢速维度不随时间下降（§13J.19）
    assert r.dimensions.attachment == 0.5
    assert r.dimensions.resentment == 0.5


def test_first_impression_flag():
    owner = RelationshipOwner()
    state = owner.resolve(RelationshipState(), [
        _inf(INFLUENCE_FORM, {"target_id": "B"}),
    ], None).next_state
    assert state.relationships[0].first_impression is True  # 初识 = 低稳定（§13J.14）
    updated = owner.resolve(state, [
        _inf(INFLUENCE_UPDATE, {"target_id": "B", "dimension": "closeness", "delta": 0.3}),
    ], None).next_state
    assert updated.relationships[0].first_impression is False  # 实质更新后脱离 first impression
