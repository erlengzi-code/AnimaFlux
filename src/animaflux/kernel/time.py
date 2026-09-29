"""世界时间引擎（v5.9 §22.7）。

生命逻辑只使用 World Time，与 Wall Clock 分离；系统真实时间只用于日志 / 监控。
"""

from __future__ import annotations

from datetime import datetime, timedelta


class Clock:
    """Kernel 的世界时间引擎：维护当前 World Time，按 tick 推进。"""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start if start is not None else datetime(2000, 1, 1)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        self._now += delta
        return self._now
