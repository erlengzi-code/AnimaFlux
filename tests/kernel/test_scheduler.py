"""P2 Kernel Scheduler 测试（§10 World Time 调度 / 稳定排序 / catch-up）。"""

from datetime import datetime, timedelta

import pytest

from animaflux.kernel.scheduler import CatchUpPolicy, Schedule, ScheduleType, Scheduler

T0 = datetime(2000, 1, 1)


def _s(schedule_id: str, *, schedule_type: ScheduleType = ScheduleType.ONE_SHOT, **kw) -> Schedule:
    return Schedule(
        schedule_id=schedule_id,
        owner_plugin="p",
        task_type="t",
        schedule_type=schedule_type,
        **kw,
    )


def test_next_due_time_is_minimum():
    sc = Scheduler()
    sc.add(_s("a", next_run_at=T0 + timedelta(minutes=10)))
    sc.add(_s("b", next_run_at=T0 + timedelta(minutes=5)))
    assert sc.next_due_time() == T0 + timedelta(minutes=5)


def test_next_due_time_empty_is_none():
    assert Scheduler().next_due_time() is None


def test_due_stable_ordering_time_priority_id():
    sc = Scheduler()
    later = _s("later", next_run_at=T0 + timedelta(minutes=2))
    low_pri = _s("low", next_run_at=T0 + timedelta(minutes=1), priority=0)
    high_pri = _s("high", next_run_at=T0 + timedelta(minutes=1), priority=10)
    sc.add(later)
    sc.add(low_pri)
    sc.add(high_pri)
    assert sc.due(T0 + timedelta(minutes=10)) == (high_pri, low_pri, later)


def test_due_excludes_future_and_disabled():
    sc = Scheduler()
    future = _s("future", next_run_at=T0 + timedelta(minutes=1))
    disabled = _s("disabled", next_run_at=T0, enabled=False)
    sc.add(future)
    sc.add(disabled)
    assert sc.due(T0) == ()


def test_advance_one_shot_returns_none():
    s = _s("x", next_run_at=T0)
    assert Scheduler().advance(s, T0) is None


def test_advance_fixed_interval():
    s = _s("x", schedule_type=ScheduleType.FIXED_INTERVAL, next_run_at=T0, interval=timedelta(minutes=5))
    nxt = Scheduler().advance(s, T0)
    assert nxt is not None and nxt.next_run_at == T0 + timedelta(minutes=5)


def test_advance_every_tick_unchanged():
    s = _s("x", schedule_type=ScheduleType.EVERY_TICK)
    assert Scheduler().advance(s, T0) is s


def test_duplicate_schedule_id_rejected():
    sc = Scheduler()
    sc.add(_s("x"))
    with pytest.raises(ValueError):
        sc.add(_s("x"))
