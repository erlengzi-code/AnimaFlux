"""Personality State Owner（v5.9 §13C）。

Personality = 长期相对稳定的反应倾向。它是 Bias，不是 Action Command（§13C.15.2）。
Slow State（§13C.2）：普通事件不能直接大幅修改 Trait。变化必须 evidence-driven + bounded
（§13C.6 / §13C.13）。对具体人物的 trust 属于 Relationship，不是 Personality（§13C.5）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01

INFLUENCE_SET = "personality.set"
INFLUENCE_DEVELOP = "personality.develop"

# 单次 Develop 的最大 Trait 步长（bounded，§13C.13）
MAX_TRAIT_STEP = 0.1
# 默认可塑性（§13C.6）：变化幅度按 plasticity 缩放
DEFAULT_PLASTICITY = 0.2

# v0.1 默认 Big Five-inspired Core Traits（§13C.3）；Core 不绑定 Big Five
CORE_TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "emotional_reactivity")


@dataclass(frozen=True)
class Trait:
    name: str
    value: float = 0.5


@dataclass(frozen=True)
class PersonalityState:
    traits: tuple[Trait, ...] = ()
    plasticity: float = DEFAULT_PLASTICITY


def validate(state: PersonalityState) -> None:
    for t in state.traits:
        if not (0.0 <= t.value <= 1.0):
            raise ValueError(f"trait {t.name} value out of range")
    if not (0.0 <= state.plasticity <= 1.0):
        raise ValueError("plasticity out of range")


class PersonalityOwner:
    """Personality 的 Primary Owner。Slow + bounded + evidence-driven（§13C.6）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_SET:
                state = self._set(state, inf)
                changes.append("set")
            elif t == INFLUENCE_DEVELOP:
                state = self._develop(state, inf)
                changes.append("develop")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _set(self, state: PersonalityState, inf) -> PersonalityState:
        values = inf.metadata.get("traits") or {}
        plasticity = clamp01(float(inf.metadata.get("plasticity", state.plasticity)))
        existing = {t.name: t for t in state.traits}
        for name, value in values.items():
            existing[name] = Trait(name=name, value=clamp01(float(value)))
        return replace(state, traits=tuple(existing.values()), plasticity=plasticity)

    def _develop(self, state: PersonalityState, inf) -> PersonalityState:
        trait_name = inf.metadata.get("trait")
        delta = float(inf.metadata.get("delta", 0.0))
        evidence_refs = tuple(inf.metadata.get("evidence_refs") or ())
        # 普通事件不能直接修改 Trait；无 Development Evidence → 忽略（§13C.7）
        if not evidence_refs or trait_name is None:
            return state
        step = max(-MAX_TRAIT_STEP, min(MAX_TRAIT_STEP, delta)) * state.plasticity
        traits = []
        for t in state.traits:
            if t.name == trait_name:
                traits.append(replace(t, value=clamp01(t.value + step)))
            else:
                traits.append(t)
        return replace(state, traits=tuple(traits))


def serialize(state: PersonalityState) -> dict:
    return {
        "traits": [{"name": t.name, "value": t.value} for t in state.traits],
        "plasticity": state.plasticity,
    }


def deserialize(data: dict) -> PersonalityState:
    return PersonalityState(
        traits=tuple(Trait(name=t["name"], value=t["value"]) for t in data["traits"]),
        plasticity=data.get("plasticity", DEFAULT_PLASTICITY),
    )
