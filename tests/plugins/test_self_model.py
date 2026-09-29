"""P9 Self Model Owner 测试（§13L：Domain-specific Efficacy / Evidence-driven / 主客观分离）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.self_model import (
    INFLUENCE_EFFICACY,
    INFLUENCE_UPDATE,
    SelfModelOwner,
    SelfModelState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="self_model",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_efficacy_is_domain_specific():
    # Self-Efficacy 按领域分开，没有单一全局能力分（§13L.6）
    owner = SelfModelOwner()
    state = owner.resolve(SelfModelState(), [
        _inf(INFLUENCE_EFFICACY, {"domain": "math", "assessment": 0.9, "evidence_refs": ("EV-1",)}, "E-1"),
        _inf(INFLUENCE_EFFICACY, {"domain": "social", "assessment": 0.2, "evidence_refs": ("EV-2",)}, "E-2"),
    ], None).next_state
    by_domain = {a.domain: a.assessment for a in state.self_efficacy}
    assert by_domain == {"math": 0.9, "social": 0.2}  # 领域独立（§13L.6）
    assert not hasattr(state, "global_competence")  # 无全局分


def test_update_requires_evidence():
    owner = SelfModelOwner()
    out = owner.resolve(SelfModelState(), [
        _inf(INFLUENCE_UPDATE, {"view": "current", "domain": "work", "dimension": "competence", "assessment": 0.8}),
    ], None).next_state
    assert len(out.current_self) == 0  # 无证据不写入（§13L.7）


def test_current_vs_ideal_discrepancy_preserved():
    owner = SelfModelOwner()
    state = owner.resolve(SelfModelState(), [
        _inf(INFLUENCE_UPDATE, {"view": "current", "domain": "work", "dimension": "competence", "assessment": 0.3, "evidence_refs": ("EV-1",)}),
        _inf(INFLUENCE_UPDATE, {"view": "ideal", "domain": "work", "dimension": "competence", "assessment": 0.9, "evidence_refs": ("EV-2",)}),
    ], None).next_state
    assert state.current_self[0].assessment == 0.3
    assert state.ideal_self[0].assessment == 0.9  # 落差保留，不强行一致（§13L.3）


def test_identity_is_not_self_model():
    # Self Model 是主观评价，不含 Identity 的身份事实字段（§13L.2）
    state = SelfModelState()
    assert not hasattr(state, "name")
    assert not hasattr(state, "agent_id")
    assert hasattr(state, "self_esteem")  # 主观评价维度在
