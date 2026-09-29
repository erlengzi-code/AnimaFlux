"""Reflection Process（v5.9 §14F）。

Reflection 是低频、长时间尺度、模式与意义导向的 Process，不新增 Core State（§14F）。
它只产出 ReflectionResult（结构化 Cognitive Artifact），其中的 Proposal / Evidence 供
对应 Owner 决定是否采纳，Reflection 自身不直接修改任何 Core State（§14F.4）。
PatternCandidate 不是 Personality Fact / Belief，未采纳前只是候选（§14F.3）。
证据不足是合法结果（§14F.12）。

v0.1 为确定性实现：对给定 evidence_items 做词频/共现统计识别重复模式，产出带 source_refs
的 Proposal / Evidence。LLM 只作为可替换能力，不在此处被调用（§15D 确定性优先）。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from animaflux.contracts.reflection import PatternCandidate, ReflectionResult
from animaflux.kernel.ids import IdGenerator
from animaflux.plugins.default_life._common import clamp01

# 出现次数达到该值才认定「重复模式」（§14F.11）
MIN_OCCURRENCE = 2

# evidence kind -> 对应 Proposal 字段映射（§14F.4 只产出 Evidence，不直接写 State）
KIND_TO_RESULT_FIELD = {
    "goal_failure": "goal_review_evidence",
    "relationship": "relationship_evidence",
    "self": "self_model_evidence",
    "value": "value_development_evidence",
    "personality": "personality_development_evidence",
}


@dataclass(frozen=True)
class EvidenceItem:
    """供 Reflection 聚合的最小证据单元（§14F.5）。"""

    item_ref: str
    kind: str          # goal_failure | relationship | self | value | personality | ...
    keyword: str
    description: str = ""


class ReflectionProcess:
    """确定性模式识别 + Proposal/Evidence 产出（§14F）。"""

    def __init__(self) -> None:
        self._ids = IdGenerator("RFL", width=None)

    def reflect(
        self,
        scope_ref: str,
        evidence_items: tuple[EvidenceItem, ...] | list[EvidenceItem],
    ) -> ReflectionResult:
        items = list(evidence_items)
        observations = tuple(i.description for i in items if i.description)
        patterns = self._detect_patterns(items)
        contradictions = self._detect_contradictions(items)
        open_questions = self._open_questions(items)

        # 把 patterns 转成 Evidence，只挂 source_refs，不修改任何 State（§14F.4）
        result_fields = {field: [] for field in KIND_TO_RESULT_FIELD.values()}
        belief_proposals: list[str] = []
        narrative_proposals: list[str] = []
        memory_proposals: list[str] = []
        for p in patterns:
            field = KIND_TO_RESULT_FIELD.get(p.kind)
            if field is not None:
                result_fields[field].append(f"{p.pattern_id}: {p.description}")
            if p.kind == "goal_failure":
                belief_proposals.append(f"reassess feasibility behind {p.description}")
                memory_proposals.append(f"reconsolidate {p.description}")
            if p.kind == "relationship":
                narrative_proposals.append(f"relationship pattern: {p.description}")

        source_refs = tuple(dict.fromkeys(i.item_ref for i in items))
        status, confidence = self._status(items, patterns)
        return ReflectionResult(
            reflection_id=self._ids.next(),
            scope_ref=scope_ref,
            observations=observations,
            pattern_candidates=tuple(patterns),
            contradictions=contradictions,
            open_questions=open_questions,
            belief_revision_proposals=tuple(belief_proposals),
            self_model_evidence=tuple(result_fields["self_model_evidence"]),
            value_development_evidence=tuple(result_fields["value_development_evidence"]),
            personality_development_evidence=tuple(result_fields["personality_development_evidence"]),
            relationship_evidence=tuple(result_fields["relationship_evidence"]),
            goal_review_evidence=tuple(result_fields["goal_review_evidence"]),
            narrative_proposals=tuple(narrative_proposals),
            memory_reconsolidation_proposals=tuple(memory_proposals),
            status=status,
            confidence=confidence,
            source_refs=source_refs,
            trace={"items": len(items), "patterns": len(patterns)},
        )

    def _detect_patterns(self, items: list[EvidenceItem]) -> list[PatternCandidate]:
        counter = Counter((i.kind, i.keyword) for i in items)
        patterns = []
        for (kind, keyword), count in counter.items():
            if count < MIN_OCCURRENCE:
                continue
            refs = tuple(i.item_ref for i in items if i.kind == kind and i.keyword == keyword)
            patterns.append(
                PatternCandidate(
                    pattern_id=self._ids.next(),
                    kind=kind,
                    description=f"repeated {kind} around '{keyword}'",
                    evidence_refs=refs,
                    occurrence_count=count,
                    confidence=clamp01(min(1.0, count / 5.0)),
                )
            )
        return patterns

    @staticmethod
    def _detect_contradictions(items: list[EvidenceItem]) -> tuple[str, ...]:
        # v0.1：同一 kind 内出现两个相斥 keyword 视为待核矛盾（§14F.9）
        by_kind: dict[str, set[str]] = {}
        for i in items:
            by_kind.setdefault(i.kind, set()).add(i.keyword)
        contradictions = []
        for kind, keywords in by_kind.items():
            if len(keywords) > 1:
                contradictions.append(f"{kind}: multiple directions {sorted(keywords)}")
        return tuple(contradictions)

    @staticmethod
    def _open_questions(items: list[EvidenceItem]) -> tuple[str, ...]:
        singles = [i for i in items if i.description]
        if len(singles) == 1:
            return (f"single observation: {singles[0].description} — needs more evidence",)
        return ()

    @staticmethod
    def _status(items: list[EvidenceItem], patterns: list[PatternCandidate]) -> tuple[str, float]:
        if not items:
            return "INSUFFICIENT_EVIDENCE", 0.0
        if len(items) == 1:
            return "TENTATIVE", 0.3
        if patterns:
            return "SUPPORTED", clamp01(min(1.0, 0.5 + 0.1 * len(patterns)))
        return "INSUFFICIENT_EVIDENCE", 0.2
