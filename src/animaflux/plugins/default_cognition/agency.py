"""Proactive Agency 派生（v5.9 §12E）。

把 Active Goal / Active Need（Drive）等内部动机信号确定性映射成「主动候选」（Candidate），
作为第二条合法决策入口（§12E）：Internal Motivation → Decision → ActionIntent → Environment
→ ActionResult → Observation → Perception。

不新增 Core State（Agency 是行为性质，§12E 核心）；不调 LLM（Deterministic First §15D.2）。
候选只代表「我主观想做什么」，是否被环境支持由 supported_actions 过滤（§12E §10）。
"""

from __future__ import annotations

from animaflux.contracts.decision import Candidate
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_cognition.decision import make_candidate

# Goal 描述关键词 → 主动动作（§12E §8 候选来源：Active Goal，§13I Proposal≠Active）
GOAL_KEYWORD_TO_ACTION: dict[str, tuple[str, str]] = {
    "opportunity": ("prepare_task", "prepare to pursue the opportunity"),
    "gain": ("seek_feedback", "seek feedback to consolidate the gain"),
    "loss": ("prepare_task", "prepare to recover from the loss"),
    "threat": ("communicate", "communicate to seek safety"),
}

# Need type → 主动动作（§12E §8 候选来源：Active Drive / Need，§13E Need=我缺什么）
NEED_TO_ACTION: dict[str, tuple[str, str]] = {
    "safety": ("communicate", "communicate to seek safety"),
    "stability": ("prepare_task", "prepare against an anticipated loss"),
    "growth": ("prepare_task", "prepare to pursue an opportunity"),
    "competence": ("seek_feedback", "seek feedback to improve competence"),
}

# 信息缺口信号：低置信 ACTIVE Belief 或空 World Model → seek_feedback（§12E §8 Information Gap）
INFORMATION_GAP_CONFIDENCE_THRESHOLD = 0.5


def derive_proactive_candidates(
    *,
    goal_state,
    drive_state,
    belief_state=None,
    world_model_state=None,
    supported_actions: frozenset[str],
    id_gen: IdGenerator,
) -> tuple[Candidate, ...]:
    """确定性派生主动候选（§12E §8）。

    顺序（Satisficing 取第一个可接受，§14D.11）：Goal → Need → 信息缺口。全部按
    supported_actions 过滤 + 按 action_type 去重；无信号 → 空 tuple（NO_ACTION）。
    """
    candidates: list[Candidate] = []
    seen: set[str] = set()

    def _add(action_type: str, description: str) -> None:
        if action_type in seen or action_type not in supported_actions:
            return
        seen.add(action_type)
        candidates.append(
            make_candidate(id_gen.next(), action_type, description=description, source="policy", feasibility=1.0)
        )

    # 1) Active Goal（PROPOSED / ACTIVE / PAUSED 都是「还在想 / 在做」§13I）
    for goal in getattr(goal_state, "goals", ()) or ():
        if getattr(goal, "status", None) not in ("PROPOSED", "ACTIVE", "PAUSED"):
            continue
        description = (getattr(goal, "description", "") or "").lower()
        for keyword, (action_type, desc) in GOAL_KEYWORD_TO_ACTION.items():
            if keyword in description:
                _add(action_type, desc)
                break

    # 2) Active Need（§13E 强度 > 0 的缺口）
    for need in getattr(drive_state, "needs", ()) or ():
        need_type = getattr(need, "need_type", "")
        intensity = float(getattr(need, "intensity", 0.0) or 0.0)
        mapping = NEED_TO_ACTION.get(need_type)
        if mapping and intensity > 0.0:
            _add(*mapping)

    # 3) 信息缺口（§12E §8）：低置信 Belief 或空 World Model → 求知
    if _has_information_gap(belief_state, world_model_state):
        _add("seek_feedback", "seek feedback to fill an information gap")

    return tuple(candidates)


def _has_information_gap(belief_state, world_model_state) -> bool:
    if belief_state is not None:
        for b in getattr(belief_state, "records", ()) or ():
            if getattr(b, "status", None) != "ACTIVE":
                continue
            confidence = float(getattr(b, "confidence", 1.0) or 1.0)
            if confidence < INFORMATION_GAP_CONFIDENCE_THRESHOLD:
                return True
    if world_model_state is not None:
        return not bool(
            getattr(world_model_state, "entities", ())
            or getattr(world_model_state, "relations", ())
            or getattr(world_model_state, "causal_rules", ())
            or getattr(world_model_state, "schemas", ())
        )
    return False
