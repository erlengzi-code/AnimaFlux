"""Drive State Owner（v5.9 §13E）。

Drive = Why。Need 属于 Drive 模块内部（§13E.1），不新增第 14 个 Core State。
Need = 我缺什么；Drive = 为什么现在想行动；Goal = 我具体想做到什么（§13E.19）。
Need/Drive 使用连续强度并具有惯性（§13E.10）：短暂满足不会让长期 Need 瞬间归零。
Emotion / Need / Value 分离（§13E.5）。Need 不直接生成 Goal（§13E.8 / §13E.19.11）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_NEED_ASSESS = "drive.need_assess"
INFLUENCE_ACTIVATE = "drive.activate"
INFLUENCE_SATISFY = "drive.satisfy"
INFLUENCE_DECAY = "drive.decay"

# 惯性：Need 强度/满足向目标缓慢靠拢（§13E.10）
NEED_INERTIA = 0.3
# Drive 衰减半衰期（秒）；persistence 越高衰减越慢（§13E.9 / §13E.16）
DRIVE_DECAY_HALF_LIFE_S = 3600.0


@dataclass(frozen=True)
class Need:
    """我缺什么：重要条件缺口 / 压力（§13E.2）。"""

    need_id: str
    need_type: str
    intensity: float = 0.0      # 缺口 / 压力强度 [0, 1]
    satisfaction: float = 1.0   # 满足度 [0, 1]
    sources: tuple[str, ...] = ()
    last_assessed_at: datetime | None = None


@dataclass(frozen=True)
class ActiveDrive:
    """为什么现在想行动：已激活的动机力量（§13E.6）。"""

    drive_id: str
    drive_type: str
    activation: float = 0.0
    urgency: float = 0.0
    persistence: float = 1.0
    source_need_refs: tuple[str, ...] = ()
    goal_refs: tuple[str, ...] = ()
    started_at: datetime | None = None


@dataclass(frozen=True)
class DriveState:
    needs: tuple[Need, ...] = ()
    active_drives: tuple[ActiveDrive, ...] = ()


def validate(state: DriveState) -> None:
    for n in state.needs:
        if not (0.0 <= n.intensity <= 1.0):
            raise ValueError(f"need {n.need_id} intensity out of range")
        if not (0.0 <= n.satisfaction <= 1.0):
            raise ValueError(f"need {n.need_id} satisfaction out of range")
    for d in state.active_drives:
        if not (0.0 <= d.activation <= 1.0):
            raise ValueError(f"drive {d.drive_id} activation out of range")
        if not (0.0 <= d.urgency <= 1.0):
            raise ValueError(f"drive {d.drive_id} urgency out of range")


class DriveOwner:
    """Drive 的 Primary Owner。确定性动机动态（§13E.16 默认不调 LLM）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_NEED_ASSESS:
                state = self._assess_need(state, inf)
                changes.append(f"assess {inf.metadata.get('need_type', '?')}")
            elif t == INFLUENCE_ACTIVATE:
                state = self._activate(state, inf)
                changes.append(f"activate {inf.metadata.get('drive_type', '?')}")
            elif t == INFLUENCE_SATISFY:
                state = self._satisfy(state, inf)
                changes.append(f"satisfy {inf.metadata.get('need_type', '?')}")
            elif t == INFLUENCE_DECAY:
                state = self._decay(state, inf)
                changes.append("decay drives")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _assess_need(self, state: DriveState, inf) -> DriveState:
        need_type = inf.metadata.get("need_type", "unknown")
        target_intensity = clamp01(float(inf.metadata.get("intensity", 0.0)))
        target_satisfaction = clamp01(float(inf.metadata.get("satisfaction", 1.0 - target_intensity)))
        sources = tuple(inf.metadata.get("sources") or ())
        now = inf.created_at
        existing = next((n for n in state.needs if n.need_type == need_type), None)
        if existing is None:
            need = Need(
                need_id=inf.influence_id, need_type=need_type,
                intensity=target_intensity, satisfaction=target_satisfaction,
                sources=sources, last_assessed_at=now,
            )
            return replace(state, needs=state.needs + (need,))
        # 惯性：向新评估值缓慢靠拢，不瞬间跳变（§13E.10）
        needs = tuple(
            replace(
                n,
                intensity=n.intensity + NEED_INERTIA * (target_intensity - n.intensity),
                satisfaction=n.satisfaction + NEED_INERTIA * (target_satisfaction - n.satisfaction),
                sources=sources or n.sources,
                last_assessed_at=now,
            )
            if n.need_id == existing.need_id else n
            for n in state.needs
        )
        return replace(state, needs=needs)

    def _activate(self, state: DriveState, inf) -> DriveState:
        drive_type = inf.metadata.get("drive_type", "unknown")
        activation = clamp01(float(inf.metadata.get("activation", inf.magnitude)))
        urgency = clamp01(float(inf.metadata.get("urgency", 0.0)))
        persistence = clamp01(float(inf.metadata.get("persistence", 1.0)))
        source_need_refs = tuple(inf.metadata.get("source_need_refs") or ())
        now = inf.created_at
        existing = next((d for d in state.active_drives if d.drive_type == drive_type), None)
        if existing is None:
            drive = ActiveDrive(
                drive_id=inf.influence_id, drive_type=drive_type,
                activation=activation, urgency=urgency, persistence=persistence,
                source_need_refs=source_need_refs, started_at=now,
            )
            return replace(state, active_drives=state.active_drives + (drive,))
        drives = tuple(
            replace(
                d,
                activation=max(d.activation, activation),
                urgency=max(d.urgency, urgency),
                source_need_refs=tuple(dict.fromkeys(d.source_need_refs + source_need_refs)),
            )
            if d.drive_id == existing.drive_id else d
            for d in state.active_drives
        )
        return replace(state, active_drives=drives)

    def _satisfy(self, state: DriveState, inf) -> DriveState:
        need_type = inf.metadata.get("need_type")
        if need_type is None:
            return state
        amount = clamp01(float(inf.metadata.get("amount", 0.0)))
        needs = []
        for n in state.needs:
            if n.need_type != need_type:
                needs.append(n)
                continue
            satisfaction = clamp01(n.satisfaction + amount)
            target_intensity = 1.0 - satisfaction
            # 惯性：满足提升后强度缓慢回落，不瞬间归零（§13E.10）
            intensity = n.intensity + NEED_INERTIA * (target_intensity - n.intensity)
            needs.append(replace(n, satisfaction=satisfaction, intensity=intensity))
        return replace(state, needs=tuple(needs))

    def _decay(self, state: DriveState, inf) -> DriveState:
        delta = float(inf.metadata.get("delta_seconds", 0.0))
        if delta <= 0:
            return state
        drives = []
        for d in state.active_drives:
            half_life = DRIVE_DECAY_HALF_LIFE_S * max(0.25, d.persistence)
            factor = 0.5 ** (delta / half_life)
            drives.append(replace(d, activation=d.activation * factor, urgency=d.urgency * factor))
        return replace(state, active_drives=tuple(drives))


def serialize(state: DriveState) -> dict:
    return {
        "needs": [
            {
                "need_id": n.need_id, "need_type": n.need_type, "intensity": n.intensity,
                "satisfaction": n.satisfaction, "sources": list(n.sources),
                "last_assessed_at": iso(n.last_assessed_at),
            }
            for n in state.needs
        ],
        "active_drives": [
            {
                "drive_id": d.drive_id, "drive_type": d.drive_type, "activation": d.activation,
                "urgency": d.urgency, "persistence": d.persistence,
                "source_need_refs": list(d.source_need_refs), "goal_refs": list(d.goal_refs),
                "started_at": iso(d.started_at),
            }
            for d in state.active_drives
        ],
    }


def deserialize(data: dict) -> DriveState:
    return DriveState(
        needs=tuple(
            Need(
                need_id=n["need_id"], need_type=n["need_type"], intensity=n["intensity"],
                satisfaction=n["satisfaction"], sources=tuple(n.get("sources", ())),
                last_assessed_at=from_iso(n.get("last_assessed_at")),
            )
            for n in data["needs"]
        ),
        active_drives=tuple(
            ActiveDrive(
                drive_id=d["drive_id"], drive_type=d["drive_type"], activation=d["activation"],
                urgency=d["urgency"], persistence=d["persistence"],
                source_need_refs=tuple(d.get("source_need_refs", ())),
                goal_refs=tuple(d.get("goal_refs", ())),
                started_at=from_iso(d.get("started_at")),
            )
            for d in data["active_drives"]
        ),
    )
