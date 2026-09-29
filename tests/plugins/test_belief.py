"""P8 Belief Owner 测试（§13G：Evidence-driven / Confidence≠Stability / Revision 历史）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.belief import (
    INFLUENCE_EVIDENCE,
    INFLUENCE_FORM,
    INFLUENCE_REVISE,
    BeliefOwner,
    BeliefState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="belief",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def _evidence():
    return [{"source_type": "perception", "support": "support", "reliability": 0.7}]


def test_no_evidence_is_hypothesis_capped():
    owner = BeliefOwner()
    out = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "X", "confidence": 0.9}),
    ], None).next_state
    assert out.records[0].confidence <= 0.3  # 无证据 → 只能作为低置信 Hypothesis（§13G.44）


def test_evidence_allows_full_confidence():
    owner = BeliefOwner()
    out = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "X", "confidence": 0.7, "evidence": _evidence()}),
    ], None).next_state
    assert out.records[0].confidence == 0.7
    assert len(out.records[0].evidence) == 1


def test_confidence_and_stability_update_independently():
    owner = BeliefOwner()
    formed = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "P", "confidence": 0.5, "stability": 0.5, "evidence": _evidence()}),
    ], None).next_state
    rec = formed.records[0]
    updated = owner.resolve(formed, [
        _inf(INFLUENCE_EVIDENCE, {"belief_id": rec.belief_id, "support": "support", "reliability": 0.8, "directness": 0.8}),
    ], None).next_state
    rec2 = updated.records[0]
    d_conf = rec2.confidence - rec.confidence
    d_stab = rec2.stability - rec.stability
    assert d_conf > 0 and d_stab > 0
    assert d_conf > d_stab  # confidence 动得快，stability 动得慢（§13G.7）


def test_revise_keeps_history():
    owner = BeliefOwner()
    formed = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "人基本值得信任", "confidence": 0.6, "evidence": _evidence()}),
    ], None).next_state
    rec = formed.records[0]
    revised = owner.resolve(formed, [
        _inf(INFLUENCE_REVISE, {"belief_id": rec.belief_id, "new_proposition": "多数人在利益冲突时不一定可信"}),
    ], None).next_state
    rec2 = revised.records[0]
    assert rec2.proposition == "多数人在利益冲突时不一定可信"
    assert rec2.history == ("人基本值得信任",)  # 旧 proposition 保留在历史（§13G.14）
    assert rec2.revision == 2
    assert len(revised.records) == 1  # 旧 Belief 不 DELETE（§13G.13）


def test_contradict_weakens_but_does_not_delete():
    owner = BeliefOwner()
    formed = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "B可靠", "confidence": 0.5, "evidence": _evidence()}),
    ], None).next_state
    rec = formed.records[0]
    state = formed
    for _ in range(3):
        state = owner.resolve(state, [
            _inf(INFLUENCE_EVIDENCE, {"belief_id": rec.belief_id, "support": "contradict", "reliability": 0.9, "directness": 0.9}),
        ], None).next_state
    rec2 = state.records[0]
    assert rec2.confidence < rec.confidence
    assert len(state.records) == 1  # 未删除
    assert rec2.status in ("WEAKENED", "REJECTED")


def test_conflicting_beliefs_coexist():
    owner = BeliefOwner()
    state = owner.resolve(BeliefState(), [
        _inf(INFLUENCE_FORM, {"proposition": "A可信", "confidence": 0.7, "evidence": _evidence()}, "B-1"),
        _inf(INFLUENCE_FORM, {"proposition": "A不可信", "confidence": 0.7, "evidence": _evidence()}, "B-2"),
    ], None).next_state
    assert len(state.records) == 2  # 矛盾 Belief 共存，不自动删除（§13G.9）
