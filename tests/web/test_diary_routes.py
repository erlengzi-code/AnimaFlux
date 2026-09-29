"""Diary 路由契约测试（§13M Web 增补）。

覆盖 GET /diary（列表）、POST /diary（点击写，话题/时间段可选）。走 in-memory SQLite，
验证 envelope 形状与数据流；无 world 的生命也能写日记（日记不依赖环境）。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from animaflux.web.app import create_app
from animaflux.web.config import WebSettings


def _client():
    return TestClient(create_app(WebSettings(db_path=":memory:")))


def _create_life(c, scenario="none") -> str:
    resp = c.post("/api/v1/lives", json={"primary_name": "小林", "scenario": scenario})
    assert resp.status_code == 201
    return resp.json()["data"]["life_id"]


def test_diary_list_empty():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.get(f"/api/v1/lives/{life_id}/diary")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert "request_id" in resp.json()["meta"]


def test_write_diary_returns_entry_and_lists():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.post(f"/api/v1/lives/{life_id}/diary", json={"topic": "my first day"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["committed"] is True
        assert data["chapter_id"]
        assert data["title"]
        assert "my first day" in data["summary"]

        listed = c.get(f"/api/v1/lives/{life_id}/diary").json()["data"]
        assert len(listed) == 1
        assert listed[0]["chapter_id"] == data["chapter_id"]
        assert listed[0]["summary"] == data["summary"]


def test_write_diary_empty_body_no_world():
    with _client() as c:
        life_id = _create_life(c, scenario="none")  # 无 world 也能写日记
        resp = c.post(f"/api/v1/lives/{life_id}/diary", json={})
        assert resp.status_code == 201
        assert resp.json()["data"]["summary"]


def test_write_diary_with_time_window():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.post(
            f"/api/v1/lives/{life_id}/diary",
            json={"topic": "these days", "time_start": "2000-01-01T00:00:00", "time_end": "2000-01-31T00:00:00"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["committed"] is True
