"""Value State Owner（v5.9 §13H）。

Value = 一个人认为什么重要、值得和应该。Slow State（§13H.2）。区分 Importance（我认为
它多重要）/ Commitment（愿意付出多大代价）/ Stability（多难改变）（§13H.3）。Value 不是
概率分布：多个 Value 可以同时很高，不要求总和为 1（§13H.4）。更新 slow + bounded +
evidence-driven（§13H.17）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_FORM = "value.form"
INFLUENCE_DEVELOP = "value.develop"
INFLUENCE_REVISE = "value.revise"

# 单次 Develop 的 Importance / Commitment 最大步长（bounded，§13H.17）
MAX_VALUE_STEP = 0.1

# v0.1 默认 Value Domains（§13H.11），Core 不绑定唯一价值理论
DEFAULT_DOMAINS = (
    "family", "security", "autonomy", "achievement", "status", "loyalty", "fairness",
    "care", "honesty", "tradition", "freedom", "knowledge", "creativity", "belonging",
    "pleasure", "meaning",
)


@dataclass(frozen=True)
class ValueCommitment:
    value_id: str
    value_type: str
    importance: float = 0.5
    commitment: float = 0.5
    stability: float = 0.5
    context_scope: str | None = None
    source_refs: tuple[str, ...] = ()
    formed_at: datetime | None = None
    last_updated_at: datetime | None = None


@dataclass(frozen=True)
class ValueState:
    commitments: tuple[ValueCommitment, ...] = ()


def validate(state: ValueState) -> None:
    for v in state.commitments:
        for name in ("importance", "commitment", "stability"):
            val = getattr(v, name)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"value {v.value_id} {name} out of range")
    # 不校验 Importance 总和（§13H.4 / §13H.22）


class ValueOwner:
    """Value 的 Primary Owner。Slow + bounded + evidence-driven（§13H.17）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_FORM:
                state = self._form(state, inf)
                changes.append("form")
            elif t == INFLUENCE_DEVELOP:
                state = self._develop(state, inf)
                changes.append("develop")
            elif t == INFLUENCE_REVISE:
                state = self._revise(state, inf)
                changes.append("revise")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _form(self, state: ValueState, inf) -> ValueState:
        value = ValueCommitment(
            value_id=inf.influence_id,
            value_type=str(inf.metadata.get("value_type", "unknown")),
            importance=clamp01(float(inf.metadata.get("importance", 0.5))),
            commitment=clamp01(float(inf.metadata.get("commitment", 0.5))),
            stability=clamp01(float(inf.metadata.get("stability", 0.5))),
            context_scope=inf.metadata.get("context_scope"),
            source_refs=tuple(inf.metadata.get("source_refs") or ()),
            formed_at=inf.created_at,
            last_updated_at=inf.created_at,
        )
        return replace(state, commitments=state.commitments + (value,))

    def _develop(self, state: ValueState, inf) -> ValueState:
        value_id = inf.metadata.get("value_id")
        importance_delta = float(inf.metadata.get("importance_delta", 0.0))
        commitment_delta = float(inf.metadata.get("commitment_delta", 0.0))
        evidence_refs = tuple(inf.metadata.get("evidence_refs") or ())
        if not evidence_refs:  # 单次普通事件不直接修改 Value（§13H.7）
            return state
        commitments = []
        for v in state.commitments:
            if v.value_id != value_id:
                commitments.append(v)
                continue
            commitments.append(
                replace(
                    v,
                    importance=clamp01(v.importance + self._bounded(importance_delta)),
                    commitment=clamp01(v.commitment + self._bounded(commitment_delta)),
                    source_refs=tuple(dict.fromkeys(v.source_refs + evidence_refs)),
                    last_updated_at=inf.created_at,
                )
            )
        return replace(state, commitments=tuple(commitments))

    def _revise(self, state: ValueState, inf) -> ValueState:
        value_id = inf.metadata.get("value_id")
        new_type = inf.metadata.get("new_value_type")
        commitments = []
        for v in state.commitments:
            if v.value_id != value_id or new_type is None:
                commitments.append(v)
                continue
            commitments.append(replace(v, value_type=str(new_type), last_updated_at=inf.created_at))
        return replace(state, commitments=tuple(commitments))

    @staticmethod
    def _bounded(delta: float) -> float:
        return max(-MAX_VALUE_STEP, min(MAX_VALUE_STEP, delta))


def serialize(state: ValueState) -> dict:
    return {
        "commitments": [
            {
                "value_id": v.value_id, "value_type": v.value_type,
                "importance": v.importance, "commitment": v.commitment,
                "stability": v.stability, "context_scope": v.context_scope,
                "source_refs": list(v.source_refs),
                "formed_at": iso(v.formed_at), "last_updated_at": iso(v.last_updated_at),
            }
            for v in state.commitments
        ],
    }


def deserialize(data: dict) -> ValueState:
    return ValueState(
        commitments=tuple(
            ValueCommitment(
                value_id=v["value_id"], value_type=v["value_type"],
                importance=v.get("importance", 0.5), commitment=v.get("commitment", 0.5),
                stability=v.get("stability", 0.5), context_scope=v.get("context_scope"),
                source_refs=tuple(v.get("source_refs", ())),
                formed_at=from_iso(v.get("formed_at")),
                last_updated_at=from_iso(v.get("last_updated_at")),
            )
            for v in data["commitments"]
        ),
    )
