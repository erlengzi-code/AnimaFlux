"""Motivation & Social Cognition 派生（v5.9 §13E / §13G / §13I / §13J）。

把 AppraisalResult 转成 Drive / Belief / Relationship / Goal 的 Influence，与
`derive_emotion_influences` 平行（§15B.10 只处理 Emotion，这里处理动机与社会认知）。
确定性优先（§15D.2）：Influence 不直接写 State（§7.3），最终由各 Owner 裁决；Goal Review
只产出 proposal（§13I.6 Proposal ≠ Active）；Relationship 更新 bounded + 方向性（§13J.2/§13J.10）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from animaflux.contracts.appraisal import AppraisalResult
from animaflux.contracts.influence import Influence
from animaflux.contracts.perception import PerceivedEvent
from animaflux.contracts.state import StateNamespace
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_life._common import clamp01

# Tag → Need（§13E.5 Emotion/Need/Value 分离；Need = 我缺什么）
TAG_TO_NEED: dict[str, tuple[str, float]] = {
    "threat": ("safety", 0.7),
    "loss": ("stability", 0.6),
    "opportunity": ("growth", 0.5),
    "gain": ("competence", 0.4),
}

# Tag → Relationship 维度增量（§13J.10 bounded；方向性：针对「带来该结果的人」）
TAG_TO_RELATIONSHIP: dict[str, tuple[tuple[str, float], ...]] = {
    "threat": (("resentment", 0.15), ("trust", -0.1)),
    "gain": (("affection", 0.1), ("trust", 0.1)),
    "opportunity": (("respect", 0.05), ("trust", 0.05)),
}

# Tag → Goal 提议（§13I.6 Proposal ≠ Active；Goal ≠ Drive §13I.27）
TAG_TO_GOAL: dict[str, str] = {
    "threat": "avoid the perceived threat",
    "loss": "recover from the perceived loss",
    "opportunity": "pursue the perceived opportunity",
    "gain": "maintain the perceived gain",
}

# 显著度阈值：低于此值的 Appraisal 不形成 Belief（§13G.11 证据驱动，避免噪音）
BELIEF_FORMATION_THRESHOLD = 0.4


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return f"{content.get('type', '')} {content.get('text', '')}".strip()
    return str(content)


def derive_drive_influences(
    results: tuple[AppraisalResult, ...] | list[AppraisalResult],
    *,
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§13E：Appraisal Tag → Need 评估（drive.need_assess）。Need 不直接生成 Goal（§13E.8）。"""
    ids = id_gen or IdGenerator("INF", width=None)
    influences = []
    for r in results:
        for tag in dict.fromkeys(r.tags):
            mapping = TAG_TO_NEED.get(tag)
            if mapping is None:
                continue
            need_type, intensity = mapping
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.motivation",
                    target_state=StateNamespace.DRIVE.value,
                    influence_type="drive.need_assess",
                    magnitude=r.overall_significance,
                    created_at=world_time,
                    cause_event_refs=tuple(r.source_refs),
                    metadata={
                        "need_type": need_type,
                        "intensity": intensity,
                        "satisfaction": 1.0 - intensity,
                        "sources": tuple(r.source_refs),
                    },
                )
            )
    return tuple(influences)


def derive_belief_influences(
    results: tuple[AppraisalResult, ...] | list[AppraisalResult],
    perceived_by_ref: dict[str, PerceivedEvent],
    *,
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§13G：显著、非自我表达的感知形成 Belief（belief.form，证据驱动）。

    误感知不提供证据 → BeliefOwner 会把它压到低置信 Hypothesis（§13G.44）。
    """
    ids = id_gen or IdGenerator("INF", width=None)
    influences = []
    for r in results:
        pe = perceived_by_ref.get(r.appraisable_item_ref)
        if pe is None or pe.modality == "communication":
            continue  # 自我表达不形成世界信念（§13G.2 Memory ≠ Belief）
        if r.overall_significance < BELIEF_FORMATION_THRESHOLD:
            continue
        proposition = _to_text(pe.perceived_content)
        if not proposition:
            continue
        evidence = (
            []
            if pe.misperception
            else [
                {
                    "source_type": "perception",
                    "support": "support",
                    "source_ref": pe.perceived_event_id,
                    "reliability": clamp01(pe.confidence),
                    "directness": clamp01(pe.clarity),
                }
            ]
        )
        influences.append(
            Influence(
                influence_id=ids.next(),
                source_plugin="default_cognition.motivation",
                target_state=StateNamespace.BELIEF.value,
                influence_type="belief.form",
                magnitude=r.overall_significance,
                created_at=world_time,
                cause_event_refs=tuple(r.source_refs),
                metadata={
                    "proposition": proposition,
                    "confidence": r.confidence,
                    "evidence": evidence,
                    "belief_type": "perceptual",
                },
            )
        )
    return tuple(influences)


def derive_relationship_influences(
    results: tuple[AppraisalResult, ...] | list[AppraisalResult],
    perceived_by_ref: dict[str, PerceivedEvent],
    *,
    existing_targets: set[str] | frozenset[str],
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§13J：针对「带来该结果的人」的关系更新；新目标 form，旧目标 bounded update（§13J.14）。"""
    ids = id_gen or IdGenerator("INF", width=None)
    influences = []
    for r in results:
        pe = perceived_by_ref.get(r.appraisable_item_ref)
        if pe is None or not pe.entity_refs:
            continue
        target_id = pe.entity_refs[0]
        deltas: dict[str, float] = {}
        for tag in dict.fromkeys(r.tags):
            for dimension, delta in TAG_TO_RELATIONSHIP.get(tag, ()):
                deltas[dimension] = deltas.get(dimension, 0.0) + delta
        if not deltas:
            continue
        if target_id in existing_targets:
            for dimension, delta in deltas.items():
                influences.append(
                    Influence(
                        influence_id=ids.next(),
                        source_plugin="default_cognition.motivation",
                        target_state=StateNamespace.RELATIONSHIP.value,
                        influence_type="relationship.update",
                        magnitude=r.overall_significance,
                        created_at=world_time,
                        cause_event_refs=tuple(r.source_refs),
                        metadata={"target_id": target_id, "dimension": dimension, "delta": delta},
                    )
                )
        else:
            # 首次接触：form 新关系（First Impression §13J.14），初始维度取正向增量
            dimensions = {k: max(0.0, v) for k, v in deltas.items()}
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.motivation",
                    target_state=StateNamespace.RELATIONSHIP.value,
                    influence_type="relationship.form",
                    magnitude=r.overall_significance,
                    created_at=world_time,
                    cause_event_refs=tuple(r.source_refs),
                    metadata={
                        "target_id": target_id,
                        "dimensions": dimensions,
                        "labels": (),
                        "provenance": "appraisal",
                    },
                )
            )
    return tuple(influences)


def derive_goal_review_influences(
    results: tuple[AppraisalResult, ...] | list[AppraisalResult],
    *,
    existing_goal_descriptions: set[str] | frozenset[str],
    world_time: datetime,
    id_gen: IdGenerator | None = None,
) -> tuple[Influence, ...]:
    """§13I Goal Review：显著 Appraisal Tag 提议 Goal（propose），已存在则去重。"""
    ids = id_gen or IdGenerator("INF", width=None)
    influences = []
    seen: set[str] = set(existing_goal_descriptions)
    for r in results:
        for tag in dict.fromkeys(r.tags):
            description = TAG_TO_GOAL.get(tag)
            if description is None or description in seen:
                continue
            seen.add(description)
            influences.append(
                Influence(
                    influence_id=ids.next(),
                    source_plugin="default_cognition.motivation",
                    target_state=StateNamespace.GOAL.value,
                    influence_type="goal.propose",
                    magnitude=r.overall_significance,
                    created_at=world_time,
                    cause_event_refs=tuple(r.source_refs),
                    metadata={
                        "description": description,
                        "base_importance": r.overall_significance,
                        "urgency": r.overall_significance,
                        "source_refs": tuple(r.source_refs),
                    },
                )
            )
    return tuple(influences)
