"""Relationship State Owner（v5.9 §13J）。

Relationship = 针对具体人物的主观关系状态。Directional（§13J.2）：A→B ≠ B→A。
禁止单一 favorability（§13J.3），使用多维 Profile（Familiarity / Trust / Affection /
Attachment / Closeness / Respect / Dependence / Resentment / Obligation）。Affection ≠
当前 Emotion（§13J.5）。First Impression ≠ 成熟长期关系（§13J.14）。事件不直接写
Relationship（§13J.9），更新 bounded + history-aware（§13J.10）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, clamp_valence, from_iso, iso

INFLUENCE_FORM = "relationship.form"
INFLUENCE_UPDATE = "relationship.update"
INFLUENCE_DECAY = "relationship.decay"
INFLUENCE_LABEL = "relationship.label"

# 长期关系维度（慢速），decay 不应触碰（§13J.19）
SLOW_DIMENSIONS = ("trust", "attachment", "resentment", "dependence")
# 单次更新对慢速维度的最大步长（bounded，§13J.10）
MAX_SLOW_STEP = 0.1
# 接触 / 张力等快速维度的半衰期（秒）
FAST_DECAY_HALF_LIFE_S = 86400.0


@dataclass(frozen=True)
class RelationshipDimensions:
    familiarity: float = 0.0
    trust: float = 0.0
    affection: float = 0.0
    attachment: float = 0.0
    closeness: float = 0.0
    respect: float = 0.0
    dependence: float = 0.0
    resentment: float = 0.0
    obligation: float = 0.0


@dataclass(frozen=True)
class RelationshipProfile:
    """A 对某个 target 的主观关系状态（§13J）。"""

    target_id: str
    dimensions: RelationshipDimensions = field(default_factory=RelationshipDimensions)
    labels: tuple[str, ...] = ()
    tension: float = 0.0
    salience: float = 0.0
    first_impression: bool = True
    formed_at: datetime | None = None
    updated_at: datetime | None = None
    provenance: str | None = None


@dataclass(frozen=True)
class RelationshipState:
    relationships: tuple[RelationshipProfile, ...] = ()


def validate(state: RelationshipState) -> None:
    for r in state.relationships:
        for name in RelationshipDimensions.__dataclass_fields__:
            v = getattr(r.dimensions, name)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"relationship {r.target_id} dimension {name} out of range")
        if not (0.0 <= r.tension <= 1.0):
            raise ValueError(f"relationship {r.target_id} tension out of range")


class RelationshipOwner:
    """Relationship 的 Primary Owner。确定性、bounded、history-aware 更新（§13J.26）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_FORM:
                state = self._form(state, inf)
                changes.append(f"form {inf.metadata.get('target_id', '?')}")
            elif t == INFLUENCE_UPDATE:
                state = self._update(state, inf)
                changes.append("update")
            elif t == INFLUENCE_DECAY:
                state = self._decay(state, inf)
                changes.append("decay")
            elif t == INFLUENCE_LABEL:
                state = self._label(state, inf)
                changes.append("label")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _form(self, state: RelationshipState, inf) -> RelationshipState:
        target_id = str(inf.metadata.get("target_id", ""))
        dims_raw = inf.metadata.get("dimensions") or {}
        dims = RelationshipDimensions(
            **{k: clamp01(float(dims_raw.get(k, 0.0)))
               for k in RelationshipDimensions.__dataclass_fields__}
        )
        labels = tuple(inf.metadata.get("labels") or ())
        profile = RelationshipProfile(
            target_id=target_id, dimensions=dims, labels=labels,
            first_impression=True, formed_at=inf.created_at, updated_at=inf.created_at,
            provenance=inf.metadata.get("provenance"),
        )
        return replace(state, relationships=state.relationships + (profile,))

    def _update(self, state: RelationshipState, inf) -> RelationshipState:
        target_id = inf.metadata.get("target_id")
        dimension = inf.metadata.get("dimension")
        delta = clamp_valence(float(inf.metadata.get("delta", inf.magnitude)))
        profiles = []
        for r in state.relationships:
            if r.target_id != target_id:
                profiles.append(r)
                continue
            dims = r.dimensions
            if dimension is None:
                profiles.append(replace(r, updated_at=inf.created_at))
                continue
            cur = getattr(dims, dimension, 0.0)
            # bounded：慢速维度单次最大步长（§13J.10），快速维度全量
            step = delta
            if dimension in SLOW_DIMENSIONS:
                step = max(-MAX_SLOW_STEP, min(MAX_SLOW_STEP, delta))
            new_val = clamp01(cur + step)
            new_dims = replace(dims, **{dimension: new_val})
            # 首次实质更新即脱离 first_impression（§13J.14）
            profiles.append(
                replace(
                    r, dimensions=new_dims,
                    first_impression=(r.first_impression and abs(step) < 1e-9),
                    updated_at=inf.created_at,
                )
            )
        return replace(state, relationships=tuple(profiles))

    def _decay(self, state: RelationshipState, inf) -> RelationshipState:
        delta = float(inf.metadata.get("delta_seconds", 0.0))
        if delta <= 0:
            return state
        factor = 0.5 ** (delta / FAST_DECAY_HALF_LIFE_S)
        profiles = []
        for r in state.relationships:
            dims = r.dimensions
            # 只有快速维度衰减；trust / attachment / resentment / dependence 保持（§13J.19）
            new_dims = replace(
                dims,
                familiarity=dims.familiarity * factor,
                affection=dims.affection * factor,
                closeness=dims.closeness * factor,
                respect=dims.respect * factor,
                obligation=dims.obligation * factor,
            )
            profiles.append(
                replace(
                    r, dimensions=new_dims,
                    tension=r.tension * factor, salience=r.salience * factor,
                    updated_at=inf.created_at,
                )
            )
        return replace(state, relationships=tuple(profiles))

    def _label(self, state: RelationshipState, inf) -> RelationshipState:
        target_id = inf.metadata.get("target_id")
        label = inf.metadata.get("label")
        action = inf.metadata.get("action", "add")
        profiles = []
        for r in state.relationships:
            if r.target_id != target_id or not label:
                profiles.append(r)
                continue
            if action == "remove":
                labels = tuple(l for l in r.labels if l != label)
            elif label not in r.labels:
                labels = r.labels + (label,)
            else:
                labels = r.labels
            profiles.append(replace(r, labels=labels, updated_at=inf.created_at))
        return replace(state, relationships=tuple(profiles))


def serialize(state: RelationshipState) -> dict:
    return {
        "relationships": [
            {
                "target_id": r.target_id,
                "dimensions": {k: getattr(r.dimensions, k) for k in RelationshipDimensions.__dataclass_fields__},
                "labels": list(r.labels), "tension": r.tension, "salience": r.salience,
                "first_impression": r.first_impression,
                "formed_at": iso(r.formed_at), "updated_at": iso(r.updated_at),
                "provenance": r.provenance,
            }
            for r in state.relationships
        ],
    }


def deserialize(data: dict) -> RelationshipState:
    return RelationshipState(
        relationships=tuple(
            RelationshipProfile(
                target_id=r["target_id"],
                dimensions=RelationshipDimensions(**r["dimensions"]),
                labels=tuple(r.get("labels", ())),
                tension=r.get("tension", 0.0), salience=r.get("salience", 0.0),
                first_impression=r.get("first_impression", True),
                formed_at=from_iso(r.get("formed_at")),
                updated_at=from_iso(r.get("updated_at")),
                provenance=r.get("provenance"),
            )
            for r in data["relationships"]
        ),
    )
