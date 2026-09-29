"""Appraisal Process（v5.9 §14B）。

确定性优先（§14B.10）。Appraisal 只输出 AppraisalResult（Cognitive Artifact），不直接写任何
Core State（§14B.9 / §14B.24）；下游 Process 再把 AppraisalResult 转成 Emotion Influence
（§15B.10）。P6 是最小确定性 Appraisal：Goal / Value / Self / Relationship 等 Facet 留空，
待 P8 / P9 对应 State 落地后填充（§14B.4）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from animaflux.contracts.appraisal import AppraisableItem, AppraisalResult
from animaflux.contracts.context import RuntimeContext
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_life._common import clamp01

# 默认 Tags 的最小确定性词典（§14B.14.10「Threat/Loss/Opportunity/Gain 可作为默认 Tags，但 Core 不写死」）
TAG_LEXICON: dict[str, tuple[str, ...]] = {
    "threat": ("danger", "threat", "attack", "伤害", "威胁", "攻击", "危险"),
    "loss": ("loss", "lose", "death", "fail", "失去", "死亡", "失败"),
    "opportunity": ("opportunity", "chance", "gift", "机会", "礼物", "机遇"),
    "gain": ("gain", "success", "reward", "获得", "成功", "奖励"),
}

# Tag -> (emotion_type, valence, arousal)：§15B.10 AppraisalResult → Emotion Influence
TAG_TO_EMOTION: dict[str, tuple[str, float, float]] = {
    "threat": ("fear", -0.6, 0.7),
    "loss": ("sadness", -0.5, 0.4),
    "opportunity": ("anticipation", 0.4, 0.6),
    "gain": ("joy", 0.6, 0.4),
}

MIN_RELEVANCE = 0.05  # §14B.3 Relevance Screening 阈值


class AppraisalProcess:
    """确定性多维 Appraisal。"""

    def __init__(self) -> None:
        self._ids = IdGenerator("APR", width=None)

    def appraise(
        self,
        items: tuple[AppraisableItem, ...] | list[AppraisableItem],
        context: RuntimeContext | None = None,
        development=None,
        retrieved=None,
    ) -> tuple[AppraisalResult, ...]:
        return tuple(self._appraise_one(item, development, retrieved) for item in items)

    def _appraise_one(self, item: AppraisableItem, development=None, retrieved=None) -> AppraisalResult:
        relevance = clamp01(item.salience)
        tags = self._detect_tags(item.content)
        novelty = self._novelty(item, development, retrieved)
        # §14B.1 / §14B.8：多维，significance 由 relevance × novelty 加权，不压成单一正负
        significance = clamp01(relevance * (0.5 + 0.5 * novelty))
        if relevance < MIN_RELEVANCE:
            # §14B.3 minimal appraisal：低相关只给极低 significance，不触发情绪
            tags = ()
            significance = clamp01(relevance)
        return AppraisalResult(
            appraisal_id=self._ids.next(),
            appraisable_item_ref=item.item_ref,
            relevance=relevance,
            overall_significance=significance,
            novelty=novelty,
            expectedness=1.0 - novelty,
            certainty=clamp01(1.0 - 0.5 * novelty),
            coping_potential=self._coping(item, development),
            tags=tags,
            confidence=clamp01(relevance),
            reason_codes=("relevance_screen",) if relevance < MIN_RELEVANCE else ("deterministic_minimal",),
            source_refs=item.source_refs,
        )

    @staticmethod
    def _detect_tags(content: Any) -> tuple[str, ...]:
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, dict):
            tags = content.get("tags")
            if tags:
                return tuple(tags)
            text = f"{content.get('type', '')} {content.get('text', '')}"
        lowered = text.lower()
        return tuple(tag for tag, words in TAG_LEXICON.items() if any(w in lowered for w in words))

    @staticmethod
    def _novelty(item: AppraisableItem, development=None, retrieved=None) -> float:
        if isinstance(item.content, dict) and "novelty" in item.content:
            base = clamp01(item.content["novelty"])
        elif development is not None and isinstance(item.content, dict) and item.content.get("domain"):
            # Development Context：领域阅历越高越熟悉 → novelty 越低（§24.20）。
            # 只读 Domain Experience，不读 age（禁止 age_multiplier）。
            d = development.domain_experience.domain(item.content["domain"])
            if d is not None:
                familiarity = clamp01(d.exposure / 10.0)
                base = clamp01(1.0 - 0.8 * familiarity)
            else:
                base = 0.5
        else:
            base = 0.5
        # Retrieval familiarity：检索到相似记忆 → 更熟悉 → novelty 再降低（§24.20 / §14C）
        if retrieved is not None and getattr(retrieved, "memories", None):
            familiarity = clamp01(len(retrieved.memories) / 5.0)
            base = clamp01(base * (1.0 - 0.6 * familiarity))
        return base

    @staticmethod
    def _coping(item: AppraisableItem, development=None) -> float | None:
        # 阅历可影响主观应对资源估计（§24.20），同样不引入 age_multiplier
        if development is not None and isinstance(item.content, dict) and item.content.get("domain"):
            d = development.domain_experience.domain(item.content["domain"])
            if d is not None:
                return clamp01(0.3 + 0.7 * clamp01(d.exposure / 10.0))
        return None


def derive_emotion_influences(
    results: tuple[AppraisalResult, ...] | list[AppraisalResult],
    *,
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§15B.10：把 AppraisalResult 转成 Emotion Influence（不直接写 Emotion，§14B.9）。"""
    ids = id_gen or IdGenerator("INF", width=None)
    influences = []
    for r in results:
        for tag in r.tags:
            mapping = TAG_TO_EMOTION.get(tag)
            if mapping is None:
                continue
            emotion_type, valence, arousal = mapping
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.appraisal",
                    target_state=StateNamespace.EMOTION.value,
                    influence_type="emotion.trigger",
                    magnitude=r.overall_significance,
                    created_at=world_time,
                    cause_event_refs=tuple(r.source_refs),
                    metadata={
                        "emotion_type": emotion_type,
                        "valence": valence,
                        "arousal": arousal,
                        "trigger_refs": (r.appraisal_id,),
                    },
                )
            )
    return tuple(influences)
