"""TurnResult 契约（v5.9 §16C.9）。

`send_text()` 返回结构化 TurnResult，不直接返回裸 LLM 文本。普通用户主要使用 `text`；
高级用户可追踪 tick_id / trace_ref。`send_text()` 绝不等于 `llm.chat()`（§16C.8）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TurnResult:
    text: str
    tick_id: str
    runtime_time: str | None = None
    committed: bool = True
    action_result: Any = None
    trace_ref: str | None = None
