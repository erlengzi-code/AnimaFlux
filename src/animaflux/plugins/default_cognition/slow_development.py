"""Slow Self Development（v5.9 §13C/§13H/§13L/§13M + §14F）。

把 ReflectionResult 转成 Personality / Value / Self Model / Narrative 的 Influence，与
`derive_emotion_influences` / motivation.py 的派生平行（§14F.9）。确定性优先（§15D.2）：

- Reflection 自身只产出 Proposal / Evidence，不直接改 Slow State（§14F.4）；
- 本模块把识别出的重复模式落成 Influence，最终由各 Owner 裁决；
- Slow State 更新必须 bounded + evidence-driven（§14F.9），这里只给出小幅度、带
  evidence_refs 的方向性影响，幅度边界由 Owner 各自 enforce（§13C.13 / §13H.17 / §13L.15）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from animaflux.contracts.appraisal import AppraisalResult
from animaflux.contracts.influence import Influence
from animaflux.contracts.perception import PerceivedEvent
from animaflux.contracts.reflection import ReflectionResult
from animaflux.contracts.state import StateNamespace
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_cognition.reflection import EvidenceItem

# 可作为反思证据的情绪主题（§14B.14.10 默认 Tags，Core 不写死）。其余 Tag 不进入慢状态反思。
EVIDENCE_TAGS = ("threat", "loss", "opportunity", "gain")

# Tag → Narrative Life Theme 名（§13M.3 Life Themes）
TAG_TO_THEME: dict[str, str] = {
    "threat": "safety vigilance",
    "loss": "loss and recovery",
    "opportunity": "openness to change",
    "gain": "growth through achievement",
}

# Tag → (trait, delta)：Personality 慢更新方向（§13C.3 Big Five-inspired；delta 被 Owner 按 plasticity 缩放）
TAG_TO_PERSONALITY: dict[str, tuple[str, float]] = {
    "threat": ("emotional_reactivity", 0.15),
    "opportunity": ("openness", 0.15),
}

# Tag → self_esteem delta：反复威胁/失去轻微压低自我评价（§13L.15 bounded）
TAG_TO_SELF_ESTEEM: dict[str, float] = {
    "threat": -0.1,
    "loss": -0.08,
}

# Tag → (domain, assessment)：反复获得提升领域自我效能（§13L.6 domain-specific）
TAG_TO_SELF_EFFICACY: dict[str, tuple[str, float]] = {
    "gain": ("competence", 0.6),
}

# Tag → Value type：反复失去/获得/机遇塑造价值重要度（§13H.11 默认领域）
TAG_TO_VALUE: dict[str, str] = {
    "loss": "stability",
    "gain": "achievement",
    "opportunity": "freedom",
}


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return f"{content.get('type', '')} {content.get('text', '')}".strip()
    return str(content)


def evidence_item_for_appraisal(
    result: AppraisalResult, perceived: PerceivedEvent | None
) -> EvidenceItem | None:
    """显著 Appraisal → 反思证据单元（§14F.3/§14F.5）。

    item_ref 用 Appraisal 的 appraisable_item_ref（PerceivedEvent id），作为反思证据的
    source ref（§13M.12 Provenance）。非 EVIDENCE_TAGS 的主题不进入慢状态反思。
    """
    tag = result.tags[0] if result.tags else None
    if tag not in EVIDENCE_TAGS:
        return None
    return EvidenceItem(
        item_ref=result.appraisable_item_ref,
        kind=tag,
        keyword=tag,
        description=_to_text(perceived.perceived_content) if perceived else "",
    )


def derive_slow_influences(
    result: ReflectionResult,
    *,
    value_by_type: dict[str, str] | None = None,
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§14F.9：把 ReflectionResult 的重复模式落成慢状态 Influence（不直接写 State）。

    每个 pattern candidate 产生：一条 Narrative Theme（Provenance）+ 至少一条 bounded 的
    Personality / Self Model / Value 更新。幅度由 Owner 各自 enforce，这里只给方向与证据。
    """
    ids = id_gen or IdGenerator("INF", width=None)
    value_by_type = value_by_type or {}
    influences: list[Influence] = []
    for p in result.pattern_candidates:
        tag = p.kind
        refs = tuple(p.evidence_refs)
        if not refs:
            continue
        theme = TAG_TO_THEME.get(tag)
        if theme:
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.slow_development",
                    target_state=StateNamespace.NARRATIVE.value,
                    influence_type="narrative.add_theme",
                    magnitude=p.confidence,
                    created_at=world_time,
                    cause_event_refs=refs,
                    metadata={"name": theme, "confidence": p.confidence, "source_refs": list(refs)},
                )
            )
        trait = TAG_TO_PERSONALITY.get(tag)
        if trait:
            trait_name, delta = trait
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.slow_development",
                    target_state=StateNamespace.PERSONALITY.value,
                    influence_type="personality.develop",
                    magnitude=p.confidence,
                    created_at=world_time,
                    cause_event_refs=refs,
                    metadata={"trait": trait_name, "delta": delta, "evidence_refs": list(refs)},
                )
            )
        esteem_delta = TAG_TO_SELF_ESTEEM.get(tag)
        if esteem_delta is not None:
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.slow_development",
                    target_state=StateNamespace.SELF_MODEL.value,
                    influence_type="self_model.esteem_update",
                    magnitude=p.confidence,
                    created_at=world_time,
                    cause_event_refs=refs,
                    metadata={"delta": esteem_delta, "evidence_refs": list(refs)},
                )
            )
        efficacy = TAG_TO_SELF_EFFICACY.get(tag)
        if efficacy:
            domain, assessment = efficacy
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.slow_development",
                    target_state=StateNamespace.SELF_MODEL.value,
                    influence_type="self_model.efficacy_update",
                    magnitude=p.confidence,
                    created_at=world_time,
                    cause_event_refs=refs,
                    metadata={"domain": domain, "assessment": assessment, "evidence_refs": list(refs)},
                )
            )
        value_type = TAG_TO_VALUE.get(tag)
        if value_type:
            value_id = value_by_type.get(value_type)
            if value_id:
                influences.append(
                    Influence(
                        influence_id=ids.next(),
                        source_plugin="default_cognition.slow_development",
                        target_state=StateNamespace.VALUE.value,
                        influence_type="value.develop",
                        magnitude=p.confidence,
                        created_at=world_time,
                        cause_event_refs=refs,
                        metadata={
                            "value_id": value_id,
                            "importance_delta": 0.05,
                            "commitment_delta": 0.05,
                            "evidence_refs": list(refs),
                        },
                    )
                )
            else:
                influences.append(
                    Influence(
                        influence_id=ids.next(),
                        source_plugin="default_cognition.slow_development",
                        target_state=StateNamespace.VALUE.value,
                        influence_type="value.form",
                        magnitude=p.confidence,
                        created_at=world_time,
                        cause_event_refs=refs,
                        metadata={
                            "value_type": value_type,
                            "importance": 0.55,
                            "commitment": 0.5,
                            "source_refs": list(refs),
                        },
                    )
                )
    return tuple(influences)
