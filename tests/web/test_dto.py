"""Web DTO / Serializer 测试（§Web Plan §15 / §16）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from animaflux.contracts.state import StateNamespace
from animaflux.contracts.summary import HomeostasisSummary, MoodSummary
from animaflux.web.dto import envelope_err, envelope_ok, to_jsonable


def test_to_jsonable_scalars_and_primitives():
    assert to_jsonable(None) is None
    assert to_jsonable(True) is True
    assert to_jsonable(7) == 7
    assert to_jsonable(3.5) == 3.5
    assert to_jsonable("小林") == "小林"


def test_to_jsonable_datetime_and_timedelta():
    dt = datetime(2020, 5, 17, 3, 4, 5)
    assert to_jsonable(dt) == "2020-05-17T03:04:05"
    assert to_jsonable(timedelta(days=2, seconds=3661)) == timedelta(days=2, seconds=3661).total_seconds()


def test_to_jsonable_enum():
    assert to_jsonable(StateNamespace.IDENTITY) == "identity"


def test_to_jsonable_dataclass_nested():
    mood = MoodSummary(valence=0.5, arousal=0.2)
    hs = HomeostasisSummary(energy=0.9, hydration=0.7, nutrition=0.6)
    data = {"mood": mood, "homeostasis": hs, "tags": ("a", "b")}
    out = to_jsonable(data)
    assert out["mood"] == {"valence": 0.5, "arousal": 0.2}
    assert out["homeostasis"] == {"energy": 0.9, "hydration": 0.7, "nutrition": 0.6}
    assert out["tags"] == ["a", "b"]


def test_envelope_ok_shape():
    body = envelope_ok({"x": 1}, request_id="req-1", trace_ref=None)
    assert body["data"] == {"x": 1}
    assert body["meta"]["request_id"] == "req-1"
    assert body["meta"]["trace_ref"] is None


def test_envelope_err_shape():
    body = envelope_err("LIFE_NOT_FOUND", "life 'x' not found", request_id="req-2")
    assert body["error"] == {"code": "LIFE_NOT_FOUND", "message": "life 'x' not found"}
    assert body["meta"]["request_id"] == "req-2"
    assert body["meta"]["trace_ref"] is None
