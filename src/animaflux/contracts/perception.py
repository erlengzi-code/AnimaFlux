"""Perception 契约（v5.9 §14A）。

Perception 是 Process，不新增 Core State（§14A 核心定义）。
PerceivedEvent 是 Cognitive Artifact（§15B.6），不需要 Resolver。
正式坚持 Reality ≠ Observation ≠ Perception（§14A 正式坚持）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PerceivedEvent:
    """单个主观感知事件（§14A.4）。

    misperception 必须有机制来源（low_clarity / noise / occlusion …），
    不允许无来源的 LLM hallucination 被当作 Perception（§14A.5）。
    """

    perceived_event_id: str
    modality: str
    perceived_content: Any
    confidence: float
    clarity: float
    salience: float
    uncertainty: float
    noticed_at: datetime
    source_observation_refs: tuple[str, ...] = ()
    source_event_refs: tuple[str, ...] = ()
    entity_refs: tuple[str, ...] = ()
    misperception: bool = False
    misperception_cause: str | None = None


@dataclass(frozen=True)
class PerceivedEventSet:
    """Perception 的标准输出（§14A.4）。"""

    perceived_events: tuple[PerceivedEvent, ...]
    dropped_observation_refs: tuple[str, ...] = ()  # 被 Attention Budget / Sensory Gate 丢弃（§14A.6）
    trace: dict[str, Any] = field(default_factory=dict)
