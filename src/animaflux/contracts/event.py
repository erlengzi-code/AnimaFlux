"""Event 契约（v5.9 §5.6 / §5.16）。

Event = 已经确认发生的客观 Runtime 事实，创建后不可修改（frozen）。
event_type 使用命名空间（§5.14），业务内容进 payload（§5.15）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """客观事件。一个客观 Event，多份主观 Perception（§5.8）。"""

    event_id: str
    event_type: str
    world_time: datetime

    source: str | None = None
    participants: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    visibility: str = "public"
    causal_refs: tuple[str, ...] = ()
    importance_hint: float = 0.0
