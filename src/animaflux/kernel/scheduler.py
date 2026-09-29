"""Kernel Scheduler（v5.9 §10）。

Scheduler 只负责基于 World Time 的时间调度；具体 Task 语义属于 Plugin（§10.17）。
Schedule 描述未来，可 reschedule / pause / cancel（§10.16）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ScheduleType(str, Enum):
    EVERY_TICK = "every_tick"
    FIXED_INTERVAL = "fixed_interval"
    CALENDAR = "calendar"
    ONE_SHOT = "one_shot"


class CatchUpPolicy(str, Enum):
    RUN_ALL = "run_all"
    RUN_ONCE = "run_once"
    COALESCE = "coalesce"
    SKIP = "skip"


@dataclass(frozen=True)
class Schedule:
    """§10.8 基础字段。priority 只表示调度顺序，不表示业务重要性（§10.12）。"""

    schedule_id: str
    owner_plugin: str
    task_type: str
    schedule_type: ScheduleType

    next_run_at: datetime | None = None
    priority: int = 0
    catch_up_policy: CatchUpPolicy = CatchUpPolicy.RUN_ONCE
    interval: timedelta | None = None  # FIXED_INTERVAL 用
    payload: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class Scheduler:
    """基于 World Time 的调度器，不属于任何业务 Plugin。"""

    def __init__(self) -> None:
        self._schedules: dict[str, Schedule] = {}

    def add(self, schedule: Schedule) -> None:
        if schedule.schedule_id in self._schedules:
            raise ValueError(f"duplicate schedule_id '{schedule.schedule_id}'")
        self._schedules[schedule.schedule_id] = schedule

    def remove(self, schedule_id: str) -> None:
        del self._schedules[schedule_id]

    def get(self, schedule_id: str) -> Schedule:
        return self._schedules[schedule_id]

    def next_due_time(self) -> datetime | None:
        """§10.6：Time Engine 快进前询问，关键 Schedule 不能直接跨过。"""
        times = [
            s.next_run_at
            for s in self._schedules.values()
            if s.enabled and s.next_run_at is not None and s.schedule_type is not ScheduleType.EVERY_TICK
        ]
        return min(times) if times else None

    def due(self, current_time: datetime) -> tuple[Schedule, ...]:
        """到期任务，按 due_time → priority → schedule_id 稳定排序（§10.12）。

        priority 越大越先（仅同时到期时生效）。
        """
        due = [
            s
            for s in self._schedules.values()
            if s.enabled
            and (
                s.schedule_type is ScheduleType.EVERY_TICK
                or (s.next_run_at is not None and s.next_run_at <= current_time)
            )
        ]
        due.sort(key=lambda s: (s.next_run_at or current_time, -s.priority, s.schedule_id))
        return tuple(due)

    def advance(self, schedule: Schedule, current_time: datetime) -> Schedule | None:
        """运行后计算下一次触发；返回新 Schedule（None 表示已完成/停用）。

        CALENDAR 的规则解析在后续阶段细化，P2 仅支持显式 next_run_at。
        """
        if schedule.schedule_type is ScheduleType.ONE_SHOT:
            return None
        if schedule.schedule_type is ScheduleType.FIXED_INTERVAL:
            assert schedule.interval is not None, "FIXED_INTERVAL schedule requires interval"
            return replace(schedule, next_run_at=current_time + schedule.interval)
        if schedule.schedule_type is ScheduleType.EVERY_TICK:
            return schedule
        return None  # CALENDAR 占位
