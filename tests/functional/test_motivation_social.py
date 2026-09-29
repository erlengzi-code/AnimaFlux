"""③ 动机与社会认知（§13E/§13G/§13I/§13J）。

Scenario：交朋友（关系 bounded 增长）→ 从证据到信念。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.environment import Observation
from animaflux.contracts.state import StateNamespace


def test_relationship_forms_and_grows_bounded(make_influence):
    """交朋友：first impression → trust 增长 bounded（§13J.10 / §13J.14）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-friend")

    form = make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.form", 0.0,
        created_at=handle.now(),
        metadata={
            "target_id": "human-user",
            "dimensions": {"familiarity": 0.1, "trust": 0.1, "affection": 0.05},
            "labels": ("colleague",),
        },
    )
    handle.step(1.0, extra_influences=(form,))

    rel = handle.inspect(StateNamespace.RELATIONSHIP).data.relationships[0]
    assert rel.target_id == "human-user"
    assert rel.first_impression is True
    assert rel.dimensions.trust == 0.1

    # 一次 +0.3 的信任增量被 bounded：慢维度单步上限（§13J.10），并脱离 first impression（§13J.14）
    trust_up = make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.update", 0.3,
        created_at=handle.now(),
        metadata={"target_id": "human-user", "dimension": "trust", "delta": 0.3},
    )
    handle.step(1.0, extra_influences=(trust_up,))
    rel2 = handle.inspect(StateNamespace.RELATIONSHIP).data.relationships[0]
    assert 0.1 < rel2.dimensions.trust < 0.4  # 增长但未无界 +0.3
    assert rel2.first_impression is False


def test_belief_forms_from_evidence():
    """从证据到信念：显著观察 → 形成有证据的信念（§13G.11）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-belief")
    obs = Observation(
        observation_id="o1",
        modality="observation",
        content="danger ahead",
        world_time=handle.now(),
        clarity=1.0,
        intensity=1.0,
        source_entity="human",
    )
    handle.observe(obs)
    belief = handle.inspect(StateNamespace.BELIEF).data
    assert belief.records
    assert all(b.evidence for b in belief.records)  # 有感知证据支撑，非空穴来风
