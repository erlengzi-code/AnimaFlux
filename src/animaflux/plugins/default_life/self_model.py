"""Self Model State Owner（v5.9 §13L）。

Self Model = 关于「我是谁」的自我指涉认知结构。区分 Current Self / Ideal Self / Feared Self
与领域化的 Self Evaluations（§13L.3）。Self-Efficacy 是 domain-specific 的（§13L.6），没有
单一的全局能力分。Self Model ≠ Identity（§13L.2）：Identity 是身份事实，Self Model 是主观
自我评价。评价可以是主观偏差的，不做客观正确性校验（§13L.9）。更新 evidence-driven +
bounded（§13L.15）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_UPDATE = "self_model.update"
INFLUENCE_EFFICACY = "self_model.efficacy_update"
INFLUENCE_ESTEEM = "self_model.esteem_update"
INFLUENCE_REVISE = "self_model.revise"

# 单次评估更新的最大步长（bounded，§13L.15）
MAX_ASSESSMENT_STEP = 0.1

# 三种自我观（§13L.3）
VIEWS = ("current", "ideal", "feared")


@dataclass(frozen=True)
class SelfAspect:
    """结构化的自我方面：领域 + 维度 + 评估（§13L.4）。"""

    domain: str
    dimension: str
    assessment: float = 0.5
    confidence: float = 0.5
    stability: float = 0.5
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelfModelState:
    current_self: tuple[SelfAspect, ...] = ()
    ideal_self: tuple[SelfAspect, ...] = ()
    feared_self: tuple[SelfAspect, ...] = ()
    self_efficacy: tuple[SelfAspect, ...] = ()   # domain-specific（§13L.6）
    self_esteem: float = 0.5
    body_image: float = 0.5
    role_self_views: tuple[SelfAspect, ...] = ()


def validate(state: SelfModelState) -> None:
    for name in ("current_self", "ideal_self", "feared_self", "self_efficacy", "role_self_views"):
        for a in getattr(state, name):
            for field_name in ("assessment", "confidence", "stability"):
                v = getattr(a, field_name)
                if not (0.0 <= v <= 1.0):
                    raise ValueError(f"self aspect {a.domain}.{a.dimension} {field_name} out of range")
    for field_name in ("self_esteem", "body_image"):
        v = getattr(state, field_name)
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"{field_name} out of range")


def _view_field(view: str) -> str:
    return {"current": "current_self", "ideal": "ideal_self", "feared": "feared_self"}.get(view, "")


class SelfModelOwner:
    """Self Model 的 Primary Owner。evidence-driven + bounded（§13L.15）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_UPDATE:
                state = self._update(state, inf)
                changes.append("update")
            elif t == INFLUENCE_EFFICACY:
                state = self._efficacy(state, inf)
                changes.append("efficacy")
            elif t == INFLUENCE_ESTEEM:
                state = self._esteem(state, inf)
                changes.append("esteem")
            elif t == INFLUENCE_REVISE:
                state = self._revise(state, inf)
                changes.append("revise")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _update(self, state: SelfModelState, inf) -> SelfModelState:
        view = inf.metadata.get("view", "current")
        field_name = _view_field(view)
        if not field_name:
            return state
        domain = inf.metadata.get("domain")
        dimension = inf.metadata.get("dimension")
        assessment = float(inf.metadata.get("assessment", 0.5))
        evidence_refs = tuple(inf.metadata.get("evidence_refs") or ())
        if not evidence_refs or not domain or not dimension:  # 单次普通事件不直接改写（§13L.7）
            return state
        aspect = SelfAspect(
            domain=str(domain), dimension=str(dimension),
            assessment=clamp01(assessment), confidence=clamp01(float(inf.metadata.get("confidence", 0.5))),
            stability=clamp01(float(inf.metadata.get("stability", 0.5))),
            evidence_refs=evidence_refs,
        )
        aspects = tuple(getattr(state, field_name)) + (aspect,)
        return replace(state, **{field_name: aspects})

    def _efficacy(self, state: SelfModelState, inf) -> SelfModelState:
        domain = inf.metadata.get("domain")
        assessment = float(inf.metadata.get("assessment", 0.5))
        evidence_refs = tuple(inf.metadata.get("evidence_refs") or ())
        if not evidence_refs or not domain:  # domain-specific，且 evidence-driven（§13L.6 / §13L.7）
            return state
        # 找到同 domain 已有评估则 bounded 更新，否则新增（§13L.15）
        updated = False
        aspects = []
        for a in state.self_efficacy:
            if a.domain == domain:
                step = max(-MAX_ASSESSMENT_STEP, min(MAX_ASSESSMENT_STEP, assessment - a.assessment))
                aspects.append(
                    replace(
                        a, assessment=clamp01(a.assessment + step),
                        evidence_refs=tuple(dict.fromkeys(a.evidence_refs + evidence_refs)),
                    )
                )
                updated = True
            else:
                aspects.append(a)
        if not updated:
            aspects.append(
                SelfAspect(domain=str(domain), dimension="self_efficacy",
                           assessment=clamp01(assessment), evidence_refs=evidence_refs)
            )
        return replace(state, self_efficacy=tuple(aspects))

    def _esteem(self, state: SelfModelState, inf) -> SelfModelState:
        delta = float(inf.metadata.get("delta", 0.0))
        evidence_refs = tuple(inf.metadata.get("evidence_refs") or ())
        if not evidence_refs:
            return state
        step = max(-MAX_ASSESSMENT_STEP, min(MAX_ASSESSMENT_STEP, delta))
        return replace(state, self_esteem=clamp01(state.self_esteem + step))

    def _revise(self, state: SelfModelState, inf) -> SelfModelState:
        view = inf.metadata.get("view")
        domain = inf.metadata.get("domain")
        dimension = inf.metadata.get("dimension")
        new_assessment = inf.metadata.get("assessment")
        field_name = _view_field(view)
        if not field_name or new_assessment is None:
            return state
        aspects = []
        for a in getattr(state, field_name):
            if a.domain == domain and a.dimension == dimension:
                aspects.append(replace(a, assessment=clamp01(float(new_assessment))))
            else:
                aspects.append(a)
        return replace(state, **{field_name: tuple(aspects)})


def _serialize_aspects(aspects) -> list:
    return [
        {"domain": a.domain, "dimension": a.dimension, "assessment": a.assessment,
         "confidence": a.confidence, "stability": a.stability, "evidence_refs": list(a.evidence_refs)}
        for a in aspects
    ]


def _deserialize_aspects(data) -> tuple[SelfAspect, ...]:
    return tuple(
        SelfAspect(
            domain=a["domain"], dimension=a["dimension"], assessment=a.get("assessment", 0.5),
            confidence=a.get("confidence", 0.5), stability=a.get("stability", 0.5),
            evidence_refs=tuple(a.get("evidence_refs", ())),
        )
        for a in data
    )


def serialize(state: SelfModelState) -> dict:
    return {
        "current_self": _serialize_aspects(state.current_self),
        "ideal_self": _serialize_aspects(state.ideal_self),
        "feared_self": _serialize_aspects(state.feared_self),
        "self_efficacy": _serialize_aspects(state.self_efficacy),
        "self_esteem": state.self_esteem,
        "body_image": state.body_image,
        "role_self_views": _serialize_aspects(state.role_self_views),
    }


def deserialize(data: dict) -> SelfModelState:
    return SelfModelState(
        current_self=_deserialize_aspects(data.get("current_self", ())),
        ideal_self=_deserialize_aspects(data.get("ideal_self", ())),
        feared_self=_deserialize_aspects(data.get("feared_self", ())),
        self_efficacy=_deserialize_aspects(data.get("self_efficacy", ())),
        self_esteem=data.get("self_esteem", 0.5),
        body_image=data.get("body_image", 0.5),
        role_self_views=_deserialize_aspects(data.get("role_self_views", ())),
    )
