"""Emotion State Owner（v5.9 §13D）。

Emotion = Active Emotion Episodes + Mood（§13D.20）。多情绪共存（§13D.3），禁止单一
current_emotion 作为唯一 Source of Truth。Episode 属于 Fast State，Mood 属于 Medium State
（§13D.7）。Emotion 与 Appraisal 分离（§13D.1）：这里只做确定性的情绪动态（trigger/decay/mood），
「事件意味着什么」由 Appraisal 负责（后续阶段）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, clamp_valence

INFLUENCE_TRIGGER = "emotion.trigger"
INFLUENCE_DECAY = "emotion.decay"

DECAY_HALF_LIFE_S = 600.0  # 情绪强度半衰期（秒）
INACTIVE_THRESHOLD = 0.05  # 强度低于此值视为 inactive
MOOD_PULL = 0.05  # Mood 每步向目标缓慢靠近（bounded + smoothed，§13D.11）


@dataclass(frozen=True)
class EmotionEpisode:
    episode_id: str
    emotion_type: str
    intensity: float
    valence: float
    arousal: float
    started_at: datetime
    last_updated_at: datetime
    status: str = "active"  # active | inactive
    target_ref: str | None = None
    trigger_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Mood:
    valence: float = 0.0
    arousal: float = 0.0


@dataclass(frozen=True)
class EmotionState:
    episodes: tuple[EmotionEpisode, ...] = ()
    mood: Mood = field(default_factory=Mood)


def validate(state: EmotionState) -> None:
    """Emotion 严格 Validation（§13D.19）。"""
    for e in state.episodes:
        if not (0.0 <= e.intensity <= 1.0):
            raise ValueError(f"episode {e.episode_id} intensity out of range")
        if not (-1.0 <= e.valence <= 1.0):
            raise ValueError(f"episode {e.episode_id} valence out of range")
        if not (0.0 <= e.arousal <= 1.0):
            raise ValueError(f"episode {e.episode_id} arousal out of range")
        if e.last_updated_at < e.started_at:
            raise ValueError(f"episode {e.episode_id} last_updated < started")
    if not (-1.0 <= state.mood.valence <= 1.0):
        raise ValueError("mood valence out of range")
    if not (0.0 <= state.mood.arousal <= 1.0):
        raise ValueError("mood arousal out of range")


class EmotionOwner:
    """Emotion 的 Primary Owner。情绪动力学 deterministic（§13D.17）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_TRIGGER:
                state = self._trigger(state, inf)
                changes.append(f"trigger {inf.metadata.get('emotion_type', '?')}")
            elif t == INFLUENCE_DECAY:
                delta = float(inf.metadata.get("delta_seconds", 0.0))
                state = self._decay(state, delta)
                changes.append(f"decay {delta}s")
            # 不支持的 Influence 类型：ignore（§13A.6）
        state = self._update_mood(state)
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _trigger(self, state: EmotionState, inf) -> EmotionState:
        emotion_type = inf.metadata.get("emotion_type", "unknown")
        intensity = clamp01(float(inf.metadata.get("intensity", inf.magnitude)))
        valence = clamp_valence(float(inf.metadata.get("valence", 0.0)))
        arousal = clamp01(float(inf.metadata.get("arousal", 0.5)))
        target_ref = inf.metadata.get("target_ref")
        trigger_refs = tuple(inf.metadata.get("trigger_refs") or (inf.influence_id,))
        now = inf.created_at
        # 强化同类 active episode（取较强者），否则新增（多情绪共存，§13D.3）
        same = next((e for e in state.episodes if e.emotion_type == emotion_type and e.status == "active"), None)
        if same is not None:
            episodes = tuple(
                replace(
                    e,
                    intensity=clamp01(max(e.intensity, intensity)),
                    valence=valence,
                    arousal=arousal,
                    last_updated_at=now,
                    target_ref=target_ref,
                    trigger_refs=e.trigger_refs + trigger_refs,
                )
                if e.episode_id == same.episode_id else e
                for e in state.episodes
            )
        else:
            episode = EmotionEpisode(
                episode_id=inf.influence_id, emotion_type=emotion_type, intensity=intensity,
                valence=valence, arousal=arousal, started_at=now, last_updated_at=now,
                target_ref=target_ref, trigger_refs=trigger_refs,
            )
            episodes = state.episodes + (episode,)
        return replace(state, episodes=episodes)

    def _decay(self, state: EmotionState, delta: float) -> EmotionState:
        factor = 0.5 ** (delta / DECAY_HALF_LIFE_S) if delta > 0 else 1.0
        episodes = []
        for e in state.episodes:
            if e.status != "active":
                episodes.append(e)
                continue
            intensity = e.intensity * factor
            status = "active" if intensity >= INACTIVE_THRESHOLD else "inactive"
            episodes.append(replace(e, intensity=intensity, status=status))
        return replace(state, episodes=tuple(episodes))

    def _update_mood(self, state: EmotionState) -> EmotionState:
        active = [e for e in state.episodes if e.status == "active"]
        if active:
            total = sum(e.intensity for e in active)
            valence = sum(e.valence * e.intensity for e in active) / total
            arousal = sum(e.arousal * e.intensity for e in active) / total
        else:
            valence, arousal = 0.0, 0.0
        new_valence = clamp_valence(state.mood.valence + MOOD_PULL * (valence - state.mood.valence))
        new_arousal = clamp01(state.mood.arousal + MOOD_PULL * (arousal - state.mood.arousal))
        return replace(state, mood=Mood(valence=new_valence, arousal=new_arousal))


def serialize(state: EmotionState) -> dict:
    return {
        "episodes": [
            {
                "episode_id": e.episode_id, "emotion_type": e.emotion_type, "intensity": e.intensity,
                "valence": e.valence, "arousal": e.arousal,
                "started_at": e.started_at.isoformat(), "last_updated_at": e.last_updated_at.isoformat(),
                "status": e.status, "target_ref": e.target_ref, "trigger_refs": list(e.trigger_refs),
            }
            for e in state.episodes
        ],
        "mood": {"valence": state.mood.valence, "arousal": state.mood.arousal},
    }


def deserialize(data: dict) -> EmotionState:
    return EmotionState(
        episodes=tuple(
            EmotionEpisode(
                episode_id=e["episode_id"], emotion_type=e["emotion_type"], intensity=e["intensity"],
                valence=e["valence"], arousal=e["arousal"],
                started_at=datetime.fromisoformat(e["started_at"]),
                last_updated_at=datetime.fromisoformat(e["last_updated_at"]),
                status=e.get("status", "active"), target_ref=e.get("target_ref"),
                trigger_refs=tuple(e.get("trigger_refs", ())),
            )
            for e in data["episodes"]
        ),
        mood=Mood(valence=data["mood"]["valence"], arousal=data["mood"]["arousal"]),
    )
