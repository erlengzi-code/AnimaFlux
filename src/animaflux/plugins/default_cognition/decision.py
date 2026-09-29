"""Decision Process（v5.9 §14D）。

Decision = 现在选哪个方向。是 Process，不新增 Core State（§14D 核心定义）。Bounded
Rationality（§14D.1）：只在有限 Candidate / Context / Budget 下做选择。四阶段：Framing
→ Candidate Generation → Evaluation → Selection（§14D.4）。Satisficing（§14D.11）：
找到第一个足够可接受的方案即停，不求全局最优。不直接修改任何 Core State（§14D.27）。

v0.1 为确定性策略：简单 Decision 优先 deterministic / policy（§14D.43），LLM-assisted
留给复杂社会推理的后续阶段。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from animaflux.contracts.decision import (
    Candidate,
    CandidateEvaluation,
    DecisionFrame,
    DecisionResult,
    DecisionTriggerType,
)
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_life._common import clamp01

ACCEPTABILITY_THRESHOLD = 0.3  # Subjective Feasibility 低于此值视为不可接受（§14D.7）
HARD_RISK_THRESHOLD = 0.9      # 风险高于此值视为硬约束（§14D.12）


class DecisionProcess:
    """四阶段确定性决策（§14D.4 / §14D.12）。"""

    def __init__(self, *, candidate_budget: int = 5) -> None:
        self.candidate_budget = candidate_budget
        self._ids = IdGenerator("DEC", width=None)

    # -- 阶段一：Framing（§14D.5） --
    def frame(
        self,
        problem: str,
        *,
        trigger_refs: tuple[str, ...] = (),
        goal_refs: tuple[str, ...] = (),
        urgency: float = 0.0,
        time_horizon: str = "immediate",
        constraints: tuple[str, ...] = (),
        uncertainties: tuple[str, ...] = (),
        trigger_type: str = DecisionTriggerType.EXTERNAL.value,
    ) -> DecisionFrame:
        return DecisionFrame(
            frame_id=self._ids.next(),
            decision_problem=problem,
            trigger_refs=trigger_refs,
            trigger_type=trigger_type,
            relevant_goal_refs=goal_refs,
            time_horizon=time_horizon,
            urgency=clamp01(urgency),
            known_constraints=constraints,
            uncertainties=uncertainties,
        )

    # -- 阶段三：Candidate Evaluation（§14D.9） --
    def evaluate(self, candidate: Candidate, frame: DecisionFrame | None = None) -> CandidateEvaluation:
        feasibility = clamp01(candidate.feasibility)
        hard_violation = feasibility <= 0.0
        risk = clamp01((1.0 - feasibility) * 0.5)
        hard_violation = hard_violation or risk > HARD_RISK_THRESHOLD
        return CandidateEvaluation(
            candidate_ref=candidate.candidate_id,
            feasibility=feasibility,
            risk=risk,
            uncertainty=0.5,
            urgency=frame.urgency if frame else 0.0,
            hard_violation=hard_violation,
        )

    # -- 全流程：四阶段（§14D.4） --
    def decide(
        self,
        frame: DecisionFrame,
        candidates: Iterable[Candidate],
    ) -> DecisionResult:
        # 阶段二：Candidate Generation — 预算约束（§14D.6）
        bounded = list(candidates)[: self.candidate_budget]
        # 阶段三：Evaluation
        evaluations = {c.candidate_id: self.evaluate(c, frame) for c in bounded}
        # 阶段四：Selection — Satisficing（§14D.11），按给定顺序取第一个可接受
        rejected: list[str] = []
        selected: Candidate | None = None
        for c in bounded:
            ev = evaluations[c.candidate_id]
            if ev.hard_violation:
                rejected.append(c.candidate_id)
                continue
            if ev.feasibility < ACCEPTABILITY_THRESHOLD:
                rejected.append(c.candidate_id)
                continue
            selected = c
            break
        rejected.extend(c.candidate_id for c in bounded if c is not selected and c.candidate_id not in rejected)

        no_action_reason = None
        if selected is None:
            no_action_reason = "NO_ACTION: no acceptable candidate"

        return DecisionResult(
            decision_id=self._ids.next(),
            frame_ref=frame.frame_id,
            selected_candidate_ref=selected.candidate_id if selected else None,
            selected_intent=None,  # Intent 实现由下游 Planning / Communication 负责（§14D.16）
            rejected_candidate_refs=tuple(rejected),
            uncertainty=evaluations[selected.candidate_id].uncertainty if selected else 0.5,
            confidence=evaluations[selected.candidate_id].feasibility if selected else 0.0,
            no_action_reason=no_action_reason,
            source_refs=frame.trigger_refs,
            trace={
                "stages": ("framing", "generation", "evaluation", "selection"),
                "evaluated": len(bounded),
                "candidate_budget": self.candidate_budget,
            },
        )


def make_candidate(
    candidate_id: str,
    action_type: str,
    *,
    description: str = "",
    source: str = "policy",
    feasibility: float = 1.0,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        action_type=action_type,
        description=description,
        source=source,
        feasibility=clamp01(feasibility),
    )
