"""P2 Kernel 时间 / ID / EventQueue 测试。"""

from datetime import datetime, timedelta

from animaflux.contracts import Event
from animaflux.kernel.events import EventQueue
from animaflux.kernel.ids import IdGenerator
from animaflux.kernel.time import Clock


def test_id_generator_monotonic_and_padded():
    g = IdGenerator("EVT")
    assert g.next() == "EVT-000001"
    assert g.next() == "EVT-000002"


def test_id_generator_no_padding():
    g = IdGenerator("INF", width=None)
    assert g.next() == "INF-1"
    assert g.next() == "INF-2"


def test_clock_advances_world_time():
    c = Clock(start=datetime(2000, 1, 1))
    assert c.now() == datetime(2000, 1, 1)
    c.advance(timedelta(minutes=5))
    assert c.now() == datetime(2000, 1, 1, 0, 5)


def test_event_queue_fifo_drain():
    q = EventQueue()
    e1 = Event(event_id="EVT-1", event_type="a", world_time=datetime(2000, 1, 1))
    e2 = Event(event_id="EVT-2", event_type="b", world_time=datetime(2000, 1, 1))
    q.enqueue(e1)
    q.enqueue(e2)
    assert len(q) == 2
    assert q.drain() == (e1, e2)
    assert len(q) == 0
    assert q.drain() == ()
