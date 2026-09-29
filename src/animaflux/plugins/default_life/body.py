"""Body State Owner（v5.9 §13B）。

Body 表示客观生理状态 + 身体能力边界（§13B.1），不表示主观身体体验。七个核心区域：
Constitution / Life Cycle / Homeostasis / Health&Damage / Sleep&Fatigue / Capabilities /
Appearance（§13B.2）。chronological_age 由 Identity 派生，Body 只保存 biological_age（§13B.4）；
vital_status 由 Body 权威管理（§13B.4）。BodyOwner 默认不调用 LLM（§13B.16）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01

INFLUENCE_TIME_UPDATE = "body.time_update"
INFLUENCE_PHYSICAL_DAMAGE = "body.physical_damage"
INFLUENCE_SLEEP = "body.sleep"
INFLUENCE_NUTRITION_INTAKE = "body.nutrition_intake"
INFLUENCE_HYDRATION_INTAKE = "body.hydration_intake"
INFLUENCE_HEALING = "body.healing"
INFLUENCE_ILLNESS = "body.illness_onset"

# 单位：每秒变化速率（§13B.12 Fast 动态）
ENERGY_DRAIN_PER_S = 0.00002
HYDRATION_DRAIN_PER_S = 0.00003
NUTRITION_DRAIN_PER_S = 0.000015
FATIGUE_GAIN_PER_S = 0.00003
SLEEP_DEBT_GAIN_PER_S = 0.00002
FATIGUE_RECOVER_PER_S = 0.00008
SLEEP_DEBT_RECOVER_PER_S = 0.00006
PAIN_DECAY_PER_S = 0.00001
STRESS_DECAY_PER_S = 0.00002


@dataclass(frozen=True)
class Constitution:
    recovery_capacity: float = 0.5
    endurance_baseline: float = 0.5
    sleep_need: float = 0.5
    pain_sensitivity: float = 0.5
    aging_tendency: float = 0.5


@dataclass(frozen=True)
class Homeostasis:
    energy: float = 1.0
    hydration: float = 1.0
    nutrition: float = 1.0
    physical_stress: float = 0.0


@dataclass(frozen=True)
class Health:
    general_health: float = 1.0
    pain_signal: float = 0.0
    injuries: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Sleep:
    fatigue: float = 0.0
    sleep_debt: float = 0.0
    sleep_state: str = "awake"  # awake | asleep
    recent_sleep_quality: float = 0.5


@dataclass(frozen=True)
class Capabilities:
    mobility: float = 1.0
    strength: float = 0.5
    endurance: float = 0.5
    fine_motor: float = 0.5
    speech: float = 1.0
    vision: float = 1.0
    hearing: float = 1.0


@dataclass(frozen=True)
class BodyState:
    biological_age: float = 0.0
    vital_status: str = "ALIVE"  # ALIVE | DYING | DEAD
    constitution: Constitution = field(default_factory=Constitution)
    homeostasis: Homeostasis = field(default_factory=Homeostasis)
    health: Health = field(default_factory=Health)
    sleep: Sleep = field(default_factory=Sleep)
    capabilities: Capabilities = field(default_factory=Capabilities)
    appearance: dict[str, str] = field(default_factory=dict)


def validate(body: BodyState) -> None:
    """Body 严格数值 Validation（§13B.17）。"""

    def check(name: str, value: float) -> None:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"{name} out of range [0,1]: {value}")

    check("energy", body.homeostasis.energy)
    check("hydration", body.homeostasis.hydration)
    check("nutrition", body.homeostasis.nutrition)
    check("physical_stress", body.homeostasis.physical_stress)
    check("general_health", body.health.general_health)
    check("pain_signal", body.health.pain_signal)
    check("fatigue", body.sleep.fatigue)
    check("sleep_debt", body.sleep.sleep_debt)
    check("recent_sleep_quality", body.sleep.recent_sleep_quality)
    if body.biological_age < 0:
        raise ValueError("biological_age must be >= 0")
    if body.vital_status not in ("ALIVE", "DYING", "DEAD"):
        raise ValueError(f"invalid vital_status {body.vital_status}")
    if body.sleep.sleep_state not in ("awake", "asleep"):
        raise ValueError(f"invalid sleep_state {body.sleep.sleep_state}")


class BodyOwner:
    """Body 的 Primary Owner。生理机制 deterministic（§13B.16）。"""

    def resolve(self, current_state, influences, context):
        body = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_TIME_UPDATE:
                delta = float(inf.metadata.get("delta_seconds", 0.0))
                body = self._time_update(body, delta)
                changes.append(f"time_update {delta}s")
            elif t == INFLUENCE_PHYSICAL_DAMAGE:
                amount = float(inf.magnitude)
                body = self._damage(body, amount, inf.metadata.get("source"))
                changes.append(f"damage {amount}")
            elif t == INFLUENCE_SLEEP:
                body = self._sleep(
                    body, float(inf.metadata.get("duration_seconds", 0.0)), float(inf.magnitude)
                )
                changes.append("sleep")
            elif t == INFLUENCE_NUTRITION_INTAKE:
                body = replace(
                    body,
                    homeostasis=replace(
                        body.homeostasis,
                        nutrition=clamp01(body.homeostasis.nutrition + inf.magnitude),
                    ),
                )
            elif t == INFLUENCE_HYDRATION_INTAKE:
                body = replace(
                    body,
                    homeostasis=replace(
                        body.homeostasis,
                        hydration=clamp01(body.homeostasis.hydration + inf.magnitude),
                    ),
                )
            elif t == INFLUENCE_HEALING:
                body = replace(
                    body,
                    health=replace(
                        body.health,
                        general_health=clamp01(body.health.general_health + inf.magnitude),
                        pain_signal=clamp01(body.health.pain_signal - inf.magnitude),
                    ),
                )
            elif t == INFLUENCE_ILLNESS:
                cond = inf.metadata.get("condition", "illness")
                body = replace(
                    body,
                    health=replace(
                        body.health,
                        general_health=clamp01(body.health.general_health - inf.magnitude),
                        conditions=body.health.conditions + (cond,),
                    ),
                )
            # 不支持的 Influence 类型：ignore（§13A.6）
        body = self._evaluate_vital_status(body)
        validate(body)
        return StateResolutionResult(
            next_state=body, changed=(body != current_state), trace={"changes": changes},
        )

    def _time_update(self, body: BodyState, delta: float) -> BodyState:
        s = body.sleep
        h = body.homeostasis
        if s.sleep_state == "asleep":
            fatigue = clamp01(s.fatigue - FATIGUE_RECOVER_PER_S * delta)
            sleep_debt = clamp01(s.sleep_debt - SLEEP_DEBT_RECOVER_PER_S * delta)
            energy = clamp01(h.energy + FATIGUE_RECOVER_PER_S * delta * 0.5)
        else:
            fatigue = clamp01(s.fatigue + FATIGUE_GAIN_PER_S * delta)
            sleep_debt = clamp01(s.sleep_debt + SLEEP_DEBT_GAIN_PER_S * delta)
            energy = clamp01(h.energy - ENERGY_DRAIN_PER_S * delta)
        hydration = clamp01(h.hydration - HYDRATION_DRAIN_PER_S * delta)
        nutrition = clamp01(h.nutrition - NUTRITION_DRAIN_PER_S * delta)
        stress = clamp01(h.physical_stress - STRESS_DECAY_PER_S * delta)
        pain = clamp01(body.health.pain_signal - PAIN_DECAY_PER_S * delta)
        return replace(
            body,
            homeostasis=replace(h, energy=energy, hydration=hydration, nutrition=nutrition, physical_stress=stress),
            sleep=replace(s, fatigue=fatigue, sleep_debt=sleep_debt),
            health=replace(body.health, pain_signal=pain),
        )

    def _damage(self, body: BodyState, amount: float, source: str | None) -> BodyState:
        h = body.health
        general_health = clamp01(h.general_health - amount)
        pain_signal = clamp01(max(h.pain_signal, amount * body.constitution.pain_sensitivity))
        injuries = h.injuries + (source or "injury",) if amount >= 0.5 else h.injuries
        return replace(
            body,
            health=replace(h, general_health=general_health, pain_signal=pain_signal, injuries=injuries),
        )

    def _sleep(self, body: BodyState, duration_seconds: float, quality: float) -> BodyState:
        s = body.sleep
        h = body.homeostasis
        fatigue = clamp01(s.fatigue - FATIGUE_RECOVER_PER_S * duration_seconds)
        sleep_debt = clamp01(s.sleep_debt - SLEEP_DEBT_RECOVER_PER_S * duration_seconds)
        energy = clamp01(h.energy + FATIGUE_RECOVER_PER_S * duration_seconds * 0.5)
        return replace(
            body,
            sleep=replace(s, fatigue=fatigue, sleep_debt=sleep_debt, recent_sleep_quality=clamp01(quality)),
            homeostasis=replace(h, energy=energy),
        )

    def _evaluate_vital_status(self, body: BodyState) -> BodyState:
        """死亡必须由 Body 规则确认（§13B.16），DEAD 不可逆。"""
        if body.vital_status == "DEAD":
            return body
        if body.health.general_health <= 0.0:
            return replace(body, vital_status="DEAD")
        if body.health.general_health <= 0.2:
            return replace(body, vital_status="DYING")
        return replace(body, vital_status="ALIVE")


def serialize(body: BodyState) -> dict:
    return asdict(body)


def deserialize(data: dict) -> BodyState:
    return BodyState(
        biological_age=data["biological_age"],
        vital_status=data["vital_status"],
        constitution=Constitution(**data["constitution"]),
        homeostasis=Homeostasis(**data["homeostasis"]),
        health=Health(
            general_health=data["health"]["general_health"],
            pain_signal=data["health"]["pain_signal"],
            injuries=tuple(data["health"]["injuries"]),
            conditions=tuple(data["health"]["conditions"]),
        ),
        sleep=Sleep(**data["sleep"]),
        capabilities=Capabilities(**data["capabilities"]),
        appearance=dict(data["appearance"]),
    )
