"""Kernel Event 系统（v5.9 §5.12 / §5.17）。

Event 默认进入 Queue，由 Kernel 在对应 Life Loop 阶段统一处理，不即时递归分发（§5.12）。
"""

from __future__ import annotations

from animaflux.contracts.event import Event


class EventQueue:
    """「发生了什么」的队列，FIFO 稳定顺序（§22.5）。"""

    def __init__(self) -> None:
        self._queue: list[Event] = []

    def enqueue(self, event: Event) -> None:
        self._queue.append(event)

    def drain(self) -> tuple[Event, ...]:
        events = tuple(self._queue)
        self._queue.clear()
        return events

    def __len__(self) -> int:
        return len(self._queue)
