"""稳定 ID 生成（v5.9 §16B.31 / §22.5）。

ID 单调递增、可预测，用于 Event / Influence / Memory / Tick 等对象。
"""

from __future__ import annotations


class IdGenerator:
    """按前缀的单调计数器，生成如 ``EVT-000001`` / ``INF-1`` 的稳定 ID。"""

    def __init__(self, prefix: str, *, start: int = 1, width: int | None = 6) -> None:
        self._prefix = prefix
        self._counter = start
        self._width = width

    def next(self) -> str:
        value = self._counter
        self._counter += 1
        if self._width is None:
            return f"{self._prefix}-{value}"
        return f"{self._prefix}-{value:0{self._width}d}"
