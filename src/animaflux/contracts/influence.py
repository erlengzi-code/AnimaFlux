"""Influence 契约（v5.9 §6.18）。

Influence = 一个 Process / Plugin 对某个 State 提出的语义影响建议，不是最终 State Delta。
一条 Influence 只指向一个 target_state（§6.5）；magnitude 是影响强度，不是字段增量（§6.6）。
创建后不可修改（§6.16）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Influence:
    influence_id: str

    source_plugin: str
    target_state: str

    influence_type: str
    magnitude: float

    created_at: datetime

    confidence: float = 1.0

    duration_seconds: float | None = None
    decay: str | None = None

    cause_event_refs: tuple[str, ...] = ()
    cause_memory_refs: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(default_factory=dict)
