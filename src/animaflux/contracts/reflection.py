"""Reflection 契约（v5.9 §14F）。

Reflection 是低频、长时间尺度、模式与意义导向的 Process，不新增 Core State（§14F）。
对所有其他 State 只产生 Proposal / Evidence，不直接修改任何 Core State（§14F.4）。
ReflectionResult 是结构化 Cognitive Artifact（§14F.13）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PatternCandidate:
    """识别到的模式候选（§14F.3）。PatternCandidate 不是 Personality Fact。"""

    pattern_id: str
    kind: str          # repeated_behavior | repeated_goal_failure | relationship_pattern | belief_contradiction | value_behavior_conflict | ...
    description: str
    evidence_refs: tuple[str, ...] = ()
    occurrence_count: int = 1
    confidence: float = 0.5


@dataclass(frozen=True)
class ReflectionResult:
    """结构化反思产物（§14F.13）。"""

    reflection_id: str
    scope_ref: str
    observations: tuple[str, ...] = ()
    pattern_candidates: tuple[PatternCandidate, ...] = ()
    contradictions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    # Proposal / Evidence 只供对应 Owner 决定是否更新（§14F.4）
    belief_revision_proposals: tuple[str, ...] = ()
    self_model_evidence: tuple[str, ...] = ()
    value_development_evidence: tuple[str, ...] = ()
    personality_development_evidence: tuple[str, ...] = ()
    relationship_evidence: tuple[str, ...] = ()
    goal_review_evidence: tuple[str, ...] = ()
    narrative_proposals: tuple[str, ...] = ()
    memory_reconsolidation_proposals: tuple[str, ...] = ()
    status: str = "SUPPORTED"  # SUPPORTED | TENTATIVE | CONFLICTED | INSUFFICIENT_EVIDENCE
    confidence: float = 0.5
    source_refs: tuple[str, ...] = ()
    trace: dict = field(default_factory=dict)
