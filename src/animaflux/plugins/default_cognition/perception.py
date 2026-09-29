"""Perception Process（v5.9 §14A）。

确定性优先（§14A.11）：Sensory Gate → Attention Selection → Perceptual Interpretation →
PerceivedEventSet（§14A 核心定义 / §15B.6）。误感知必须来自机制（low clarity / noise 等），
不允许无来源的 LLM hallucination（§14A.5）。Body 决定「能不能感知」，Perception 决定
「感知到了什么」（§14A.1）。
"""

from __future__ import annotations

from typing import Any

from animaflux.contracts.context import RuntimeContext
from animaflux.contracts.environment import Observation, ObservationBatch
from animaflux.contracts.perception import PerceivedEvent, PerceivedEventSet
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_life._common import clamp01

# Sensory Gate：modality -> 所需 Body Capability（§14A.1 Body 决定能不能感知）
MODALITY_CAPABILITY = {
    "visual": "vision",
    "auditory": "hearing",
    "communication": "speech",
    "tactile": "mobility",
}

MISPERCEPTION_CLARITY = 0.4  # 低于此清晰度 → 确定误感知（§14A.5）
NOISE_MISPERCEPTION = 0.6  # 高于此噪声 → 噪声误感知（§14A.5）
DEFAULT_ATTENTION_BUDGET = 5  # §14A.2 避免全量处理所有 Observation


class PerceptionProcess:
    """确定性感知管线。可注入 attention_budget 与 id generator。"""

    def __init__(self, *, attention_budget: int = DEFAULT_ATTENTION_BUDGET) -> None:
        self._attention_budget = attention_budget
        self._ids = IdGenerator("PE", width=None)

    def perceive(
        self,
        batch: ObservationBatch,
        context: RuntimeContext | None,
        *,
        sensory_capabilities: dict[str, float] | None = None,
    ) -> PerceivedEventSet:
        sensory = sensory_capabilities or {}
        gated: list[Observation] = []
        dropped: list[str] = []
        # 1) Sensory Gate：Body 决定能不能感知（§14A.1）
        for obs in batch.observations:
            cap = MODALITY_CAPABILITY.get(obs.modality)
            if cap is not None and sensory.get(cap, 1.0) <= 0.0:
                dropped.append(obs.observation_id)
            elif obs.clarity <= 0.0:
                dropped.append(obs.observation_id)
            else:
                gated.append(obs)
        # 2) Attention Selection：有限 Budget，按 salience 稳定排序（§14A.2 / §7.6）
        ordered = sorted(gated, key=lambda o: (-o.intensity, o.observation_id))
        attended = ordered[: self._attention_budget]
        dropped.extend(o.observation_id for o in ordered[self._attention_budget :])
        # 3) Perceptual Interpretation（§14A.3）
        perceived = tuple(self._interpret(obs) for obs in attended)
        return PerceivedEventSet(
            perceived_events=perceived,
            dropped_observation_refs=tuple(dropped),
            trace={"gated": len(batch.observations), "attended": len(attended), "dropped": len(dropped)},
        )

    def _interpret(self, obs: Observation) -> PerceivedEvent:
        confidence = clamp01(obs.clarity * (1.0 - obs.noise))
        uncertainty = 1.0 - confidence
        content = obs.content
        misperception = False
        cause = None
        if obs.clarity < MISPERCEPTION_CLARITY:
            misperception, cause = True, "low_clarity"
        elif obs.noise > NOISE_MISPERCEPTION:
            misperception, cause = True, "noise"
        if misperception:
            content = self._distort(content)
        entity_refs = (obs.source_entity,) if obs.source_entity else ()
        return PerceivedEvent(
            perceived_event_id=self._ids.next(),
            modality=obs.modality,
            perceived_content=content,
            confidence=confidence,
            clarity=obs.clarity,
            salience=obs.intensity,
            uncertainty=uncertainty,
            noticed_at=obs.world_time,
            source_observation_refs=(obs.observation_id,),
            source_event_refs=obs.source_event_refs,
            entity_refs=entity_refs,
            misperception=misperception,
            misperception_cause=cause,
        )

    @staticmethod
    def _distort(content: Any) -> Any:
        """误感知的失真标记（§14A.5「听错 / 看错 / 认错」）。"""
        if isinstance(content, str):
            return f"~{content}~"
        if isinstance(content, dict):
            return {**content, "distorted": True}
        return content
