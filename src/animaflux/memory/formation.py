"""Memory Formation Process（v5.9 §13F.6 / §16B.20）。

不是所有 Event 都形成长期 Memory（§13F.6）。Memory Formation 位于 Appraisal 之后
（§16B.20 在 Consequence 后），综合 Novelty / Importance / Emotional Salience / Goal /
Self / Relationship / Repetition，产出 MemoryCandidate，再决定 persist / compress / merge /
ignore。v0.1 只实现确定性最小版：persist / ignore。

关键不变式（§13F.28.2）：Event ≠ Perception ≠ Memory。Memory 的 content 取 Perceived
Content（主观记录），绝不等于 Objective Event Log；Memory ≠ Belief ≠ Narrative（§13F.1–3）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from animaflux.contracts.appraisal import AppraisalResult
from animaflux.contracts.perception import PerceivedEvent
from animaflux.plugins.default_life._common import clamp01

# 低于此 overall_significance 的 PerceivedEvent 不形成长期 Memory（§13F.6「不是所有 Event 都形成」）。
FORMATION_THRESHOLD = 0.15

# 默认 Tags 的情绪显著度映射（§13F.6 综合 Emotional Salience）。与 appraisal.TAG_TO_EMOTION
# 语义一致但独立：Formation 只关心「情绪显著度」这一个标量，不引入 Emotion 维度耦合。
TAG_EMOTIONAL_SALIENCE: dict[str, float] = {
    "threat": 0.7,
    "loss": 0.6,
    "opportunity": 0.5,
    "gain": 0.4,
}

_MEMORY_TYPE_HINTS = ("episodic", "semantic", "procedural", "autobiographical")
_SUMMARY_MAX_CHARS = 80


@dataclass(frozen=True)
class MemoryCandidate:
    """Memory Formation 的输出（§13F.6 MemoryCandidate），尚未写入 Specialized Store。"""

    memory_type: str
    content: Any
    summary_text: str | None
    confidence: float
    importance: float
    emotional_salience: float
    source_refs: tuple[str, ...]
    provenance: str | None
    domain: str | None


class MemoryFormationProcess:
    """确定性 Memory Formation（§13F.6 最小版：persist / ignore）。

    - importance 取 Appraisal 的 overall_significance（§14B 多维评估已含 Novelty 加权）；
    - emotional_salience 取默认 Tags 的最大情绪显著度；
    - confidence 取 Perception 的 confidence（Agent 有多确信自己的感知，不代表客观准确，
      §13F.7）。
    """

    def __init__(self, *, formation_threshold: float = FORMATION_THRESHOLD) -> None:
        self._threshold = formation_threshold

    def propose(
        self,
        results: tuple[AppraisalResult, ...] | list[AppraisalResult],
        perceived_by_ref: dict[str, PerceivedEvent],
    ) -> tuple[MemoryCandidate, ...]:
        """把 (AppraisalResult → PerceivedEvent) 映射成 MemoryCandidate（§13F.6）。"""
        candidates = []
        for r in results:
            pe = perceived_by_ref.get(r.appraisable_item_ref)
            if pe is None:
                continue
            if r.overall_significance < self._threshold:
                continue  # ignore（§13F.6 不是所有 Event 都形成长期 Memory）
            candidates.append(self._candidate(r, pe))
        return tuple(candidates)

    def _candidate(self, r: AppraisalResult, pe: PerceivedEvent) -> MemoryCandidate:
        content = pe.perceived_content
        domain = content.get("domain") if isinstance(content, dict) else None
        return MemoryCandidate(
            memory_type=self._memory_type(content, pe.modality),
            content=content,
            summary_text=_summarize(content),
            confidence=clamp01(pe.confidence),
            importance=clamp01(r.overall_significance),
            emotional_salience=clamp01(max((TAG_EMOTIONAL_SALIENCE.get(t, 0.0) for t in r.tags), default=0.0)),
            source_refs=tuple(pe.source_event_refs) + tuple(pe.source_observation_refs),
            provenance="communication" if pe.modality == "communication" else "observation",
            domain=domain,
        )

    @staticmethod
    def _memory_type(content: Any, modality: str) -> str:
        """Memory Type 推断（§13F.4 四种类型）。默认 episodic；显式 hint 优先。"""
        if isinstance(content, dict):
            for key in ("memory_type", "type"):
                hint = content.get(key)
                if hint in _MEMORY_TYPE_HINTS:
                    return hint
        return "episodic"


def _summarize(content: Any) -> str | None:
    """summary_text：确定性截断，供检索展示（§13F.7 不引入单一 strength）。"""
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, dict):
        text = f"{content.get('type', '')} {content.get('text', '')}".strip()
    text = " ".join(text.split())
    if not text:
        return None
    return text[:_SUMMARY_MAX_CHARS]
