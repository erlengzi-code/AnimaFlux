"""Goal State Owner（v5.9 §13I）。

Goal = What。Goal ≠ Drive（Why）/ Plan（How）/ Action（Do）（§13I.27）。
Proposal ≠ Active（§13I.6）：想到一个 Goal 不等于真正采纳。FAILED / ABANDONED / OBSOLETE
分离（§13I.2）。Action Failure ≠ Goal Failure（§13I.16）。Priority 不使用单一永久数字
（§13I.8），区分 base importance / urgency / activation / commitment。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_PROPOSE = "goal.propose"
INFLUENCE_ADOPT = "goal.adopt"
INFLUENCE_REVIEW = "goal.review"
INFLUENCE_PROGRESS = "goal.progress"
INFLUENCE_PAUSE = "goal.pause"
INFLUENCE_RESUME = "goal.resume"
INFLUENCE_ABANDON = "goal.abandon"
INFLUENCE_COMPLETE = "goal.complete"

ACTIVE_STATUSES = ("PROPOSED", "ACTIVE", "PAUSED")


@dataclass(frozen=True)
class GoalRecord:
    """Agent 想达到的具体未来状态（§13I）。"""

    goal_id: str
    description: str
    desired_state: str | None = None
    success_criteria: tuple[str, ...] = ()
    status: str = "PROPOSED"  # PROPOSED | ACTIVE | PAUSED | ACHIEVED | FAILED | ABANDONED | OBSOLETE
    evaluation_policy: str = "subjective"  # objective | subjective | mixed
    base_importance: float = 0.5
    urgency: float = 0.0
    activation: float = 0.0
    deadline: datetime | None = None
    commitment: float = 0.0
    source_refs: tuple[str, ...] = ()
    parent_refs: tuple[str, ...] = ()
    child_refs: tuple[str, ...] = ()
    progress: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class GoalState:
    goals: tuple[GoalRecord, ...] = ()


def validate(state: GoalState) -> None:
    valid = {"PROPOSED", "ACTIVE", "PAUSED", "ACHIEVED", "FAILED", "ABANDONED", "OBSOLETE"}
    for g in state.goals:
        if g.status not in valid:
            raise ValueError(f"goal {g.goal_id} invalid status {g.status}")
        if not (0.0 <= g.base_importance <= 1.0):
            raise ValueError(f"goal {g.goal_id} base_importance out of range")


class GoalOwner:
    """Goal 的 Primary Owner。确定性目标生命周期（§13I.24 LLM 不直接改 status）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_PROPOSE:
                state = self._propose(state, inf)
                changes.append("propose")
            elif t == INFLUENCE_ADOPT:
                state = self._transition(state, inf, "ACTIVE", from_statuses=("PROPOSED",))
                changes.append("adopt")
            elif t == INFLUENCE_REVIEW:
                state = self._review(state, inf)
                changes.append("review")
            elif t == INFLUENCE_PROGRESS:
                state = self._progress(state, inf)
                changes.append("progress")
            elif t == INFLUENCE_PAUSE:
                state = self._transition(state, inf, "PAUSED", from_statuses=("ACTIVE",))
                changes.append("pause")
            elif t == INFLUENCE_RESUME:
                state = self._transition(state, inf, "ACTIVE", from_statuses=("PAUSED",))
                changes.append("resume")
            elif t == INFLUENCE_ABANDON:
                state = self._transition(state, inf, "ABANDONED", from_statuses=ACTIVE_STATUSES)
                changes.append("abandon")
            elif t == INFLUENCE_COMPLETE:
                state = self._transition(state, inf, "ACHIEVED", from_statuses=ACTIVE_STATUSES)
                changes.append("complete")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _propose(self, state: GoalState, inf) -> GoalState:
        goal = GoalRecord(
            goal_id=inf.influence_id,
            description=str(inf.metadata.get("description", "")),
            desired_state=inf.metadata.get("desired_state"),
            success_criteria=tuple(inf.metadata.get("success_criteria") or ()),
            status="PROPOSED",
            evaluation_policy=inf.metadata.get("evaluation_policy", "subjective"),
            base_importance=clamp01(float(inf.metadata.get("base_importance", 0.5))),
            urgency=clamp01(float(inf.metadata.get("urgency", 0.0))),
            deadline=inf.metadata.get("deadline"),
            source_refs=tuple(inf.metadata.get("source_refs") or ()),
            parent_refs=tuple(inf.metadata.get("parent_refs") or ()),
            created_at=inf.created_at,
            updated_at=inf.created_at,
        )
        return replace(state, goals=state.goals + (goal,))

    def _review(self, state: GoalState, inf) -> GoalState:
        goal_id = inf.metadata.get("goal_id")
        verdict = inf.metadata.get("verdict", "continue")  # continue | achieved | failed | obsolete
        status_map = {"achieved": "ACHIEVED", "failed": "FAILED", "obsolete": "OBSOLETE"}
        target = status_map.get(verdict)
        goals = []
        for g in state.goals:
            if g.goal_id != goal_id or g.status not in ACTIVE_STATUSES:
                goals.append(g)
                continue
            if target is not None:
                goals.append(replace(g, status=target, updated_at=inf.created_at))
            else:
                goals.append(replace(g, updated_at=inf.created_at))
        return replace(state, goals=tuple(goals))

    def _progress(self, state: GoalState, inf) -> GoalState:
        goal_id = inf.metadata.get("goal_id")
        milestone = str(inf.metadata.get("milestone", ""))
        goals = []
        for g in state.goals:
            if g.goal_id != goal_id or g.status not in ACTIVE_STATUSES:
                goals.append(g)
                continue
            progress = g.progress + (milestone,) if milestone else g.progress
            goals.append(replace(g, progress=progress, updated_at=inf.created_at))
        return replace(state, goals=tuple(goals))

    def _transition(self, state: GoalState, inf, target: str, *, from_statuses) -> GoalState:
        goal_id = inf.metadata.get("goal_id")
        goals = []
        for g in state.goals:
            if g.goal_id != goal_id or g.status not in from_statuses:
                goals.append(g)
                continue
            goals.append(
                replace(
                    g, status=target,
                    activation=1.0 if target == "ACTIVE" else g.activation,
                    commitment=clamp01(float(inf.metadata.get("commitment", g.commitment)))
                    if target == "ACTIVE" else g.commitment,
                    updated_at=inf.created_at,
                )
            )
        return replace(state, goals=tuple(goals))


def serialize(state: GoalState) -> dict:
    return {
        "goals": [
            {
                "goal_id": g.goal_id, "description": g.description,
                "desired_state": g.desired_state,
                "success_criteria": list(g.success_criteria), "status": g.status,
                "evaluation_policy": g.evaluation_policy,
                "base_importance": g.base_importance, "urgency": g.urgency,
                "activation": g.activation, "deadline": iso(g.deadline),
                "commitment": g.commitment, "source_refs": list(g.source_refs),
                "parent_refs": list(g.parent_refs), "child_refs": list(g.child_refs),
                "progress": list(g.progress), "created_at": iso(g.created_at),
                "updated_at": iso(g.updated_at),
            }
            for g in state.goals
        ],
    }


def deserialize(data: dict) -> GoalState:
    return GoalState(
        goals=tuple(
            GoalRecord(
                goal_id=g["goal_id"], description=g["description"],
                desired_state=g.get("desired_state"),
                success_criteria=tuple(g.get("success_criteria", ())),
                status=g.get("status", "PROPOSED"),
                evaluation_policy=g.get("evaluation_policy", "subjective"),
                base_importance=g.get("base_importance", 0.5),
                urgency=g.get("urgency", 0.0), activation=g.get("activation", 0.0),
                deadline=from_iso(g.get("deadline")),
                commitment=g.get("commitment", 0.0),
                source_refs=tuple(g.get("source_refs", ())),
                parent_refs=tuple(g.get("parent_refs", ())),
                child_refs=tuple(g.get("child_refs", ())),
                progress=tuple(g.get("progress", ())),
                created_at=from_iso(g.get("created_at")),
                updated_at=from_iso(g.get("updated_at")),
            )
            for g in data["goals"]
        ),
    )
