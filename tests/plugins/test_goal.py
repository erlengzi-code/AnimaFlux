"""P8 Goal Owner 测试（§13I：Proposal≠Active / 状态分离 / 多维 priority）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.goal import (
    INFLUENCE_ABANDON,
    INFLUENCE_ADOPT,
    INFLUENCE_PROPOSE,
    INFLUENCE_REVIEW,
    GoalOwner,
    GoalState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="goal",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_proposal_is_not_active():
    owner = GoalOwner()
    out = owner.resolve(GoalState(), [
        _inf(INFLUENCE_PROPOSE, {"description": "学会游泳"}),
    ], None).next_state
    assert out.goals[0].status == "PROPOSED"  # 想到一个 Goal ≠ 采纳（§13I.6）


def test_adopt_activates_goal():
    owner = GoalOwner()
    state = owner.resolve(GoalState(), [
        _inf(INFLUENCE_PROPOSE, {"description": "学会游泳"}),
    ], None).next_state
    gid = state.goals[0].goal_id
    adopted = owner.resolve(state, [
        _inf(INFLUENCE_ADOPT, {"goal_id": gid, "commitment": 0.6}),
    ], None).next_state
    assert adopted.goals[0].status == "ACTIVE"
    assert adopted.goals[0].commitment == 0.6


def test_failed_abandoned_obsolete_distinct():
    owner = GoalOwner()
    state = owner.resolve(GoalState(), [
        _inf(INFLUENCE_PROPOSE, {"description": "X"}),
    ], None).next_state
    gid = state.goals[0].goal_id
    active = owner.resolve(state, [_inf(INFLUENCE_ADOPT, {"goal_id": gid})], None).next_state

    failed = owner.resolve(active, [_inf(INFLUENCE_REVIEW, {"goal_id": gid, "verdict": "failed"})], None).next_state
    assert failed.goals[0].status == "FAILED"
    abandoned = owner.resolve(active, [_inf(INFLUENCE_ABANDON, {"goal_id": gid})], None).next_state
    assert abandoned.goals[0].status == "ABANDONED"
    obsolete = owner.resolve(active, [_inf(INFLUENCE_REVIEW, {"goal_id": gid, "verdict": "obsolete"})], None).next_state
    assert obsolete.goals[0].status == "OBSOLETE"


def test_no_single_priority_number():
    owner = GoalOwner()
    out = owner.resolve(GoalState(), [
        _inf(INFLUENCE_PROPOSE, {"description": "X", "base_importance": 0.5, "urgency": 0.8}),
    ], None).next_state
    g = out.goals[0]
    assert not hasattr(g, "priority")  # 无单一永久 priority（§13I.8）
    assert g.base_importance == 0.5
    assert g.urgency == 0.8
    assert g.activation == 0.0
    assert g.commitment == 0.0
