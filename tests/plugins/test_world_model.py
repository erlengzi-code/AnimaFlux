"""P9 World Model Owner 测试（§13K：主观结构 / Evidence-driven / Relation≠Relationship）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.world_model import (
    INFLUENCE_INTEGRATE,
    RelationKnowledge,
    WorldModelOwner,
    WorldModelState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="world_model",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_integrate_requires_evidence():
    # 无 belief_refs / source_refs 不允许集成（§13K.22）
    owner = WorldModelOwner()
    out = owner.resolve(WorldModelState(), [
        _inf(INFLUENCE_INTEGRATE, {"kind": "relation", "from_ref": "A", "relation_type": "manager_of", "to_ref": "B"}),
    ], None).next_state
    assert len(out.relations) == 0


def test_integrate_with_evidence_stored():
    owner = WorldModelOwner()
    out = owner.resolve(WorldModelState(), [
        _inf(INFLUENCE_INTEGRATE, {
            "kind": "relation", "from_ref": "A", "relation_type": "manager_of", "to_ref": "B",
            "belief_refs": ("BEL-1",),
        }),
    ], None).next_state
    assert len(out.relations) == 1
    assert out.relations[0].belief_refs == ("BEL-1",)


def test_world_model_is_subjective():
    # 主观结构可错：低置信的「事实」也会被存储，无客观真值修正（§13K.7）
    owner = WorldModelOwner()
    out = owner.resolve(WorldModelState(), [
        _inf(INFLUENCE_INTEGRATE, {
            "kind": "causal", "statement": "乌云预示地震", "confidence": 0.1,
            "belief_refs": ("BEL-2",),
        }, "CR-1"),
    ], None).next_state
    assert len(out.causal_rules) == 1
    assert out.causal_rules[0].confidence == 0.1  # 不被「纠正」为 0


def test_relation_model_is_not_relationship():
    # Relation Model 描述「谁是上级」，不含我对他的 trust/affection（§13K.8）
    r = RelationKnowledge(from_ref="A", relation_type="manager_of", to_ref="B")
    assert hasattr(r, "relation_type")
    assert not hasattr(r, "trust")
    assert not hasattr(r, "affection")


def test_world_model_references_not_owns_entities():
    # 用 belief_refs 指向信念，不复制 Belief 命题自身（§13K.5）
    owner = WorldModelOwner()
    out = owner.resolve(WorldModelState(), [
        _inf(INFLUENCE_INTEGRATE, {
            "kind": "entity", "entity_ref": "E-1", "label": "Alex", "belief_refs": ("BEL-3",),
        }),
    ], None).next_state
    assert out.entities[0].belief_refs == ("BEL-3",)
    assert not hasattr(out.entities[0], "proposition")  # 自身不存命题
