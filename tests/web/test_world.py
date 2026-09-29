"""World / Scenario 契约测试（§12E Web 增补）。

覆盖建生命可选场景（none / presentation / chronicle）、/act、/world、advance 自动 poll 排程事件。
全部走 in-memory SQLite（db_path=":memory:"），验证 envelope 形状与数据流（不穿透 Core）。
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


def test_create_scenario_life_reports_type():
    with _client() as c:
        life_id = _create_life(c, scenario="presentation")
        summary = c.get(f"/api/v1/lives/{life_id}").json()["data"]
        assert summary["scenario_type"] == "presentation"


def test_world_view_presentation():
    with _client() as c:
        life_id = _create_life(c, scenario="presentation")
        world = c.get(f"/api/v1/lives/{life_id}/world").json()["data"]
        assert world["scenario_type"] == "presentation"
        assert isinstance(world["facts"], dict)


def test_world_view_no_scenario():
    with _client() as c:
        life_id = _create_life(c, scenario="none")
        world = c.get(f"/api/v1/lives/{life_id}/world").json()["data"]
        assert world["scenario_type"] is None
        assert world["facts"] == {}


def test_act_on_scenario_life():
    with _client() as c:
        life_id = _create_life(c, scenario="presentation")
        resp = c.post(f"/api/v1/lives/{life_id}/act")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["acted"] is True
        # 新鲜生命（空 World Model）→ 信息缺口 → seek_feedback（确定性，§12E §8）
        assert data["action_type"] == "seek_feedback"


def test_act_on_no_world_returns_409():
    with _client() as c:
        life_id = _create_life(c, scenario="none")
        resp = c.post(f"/api/v1/lives/{life_id}/act")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NO_WORLD"


def test_advance_fires_presentation_schedule():
    with _client() as c:
        life_id = _create_life(c, scenario="presentation")
        # 无准备推进 8 天 → 演讲日（presentation_at = 2000-01-08）按 preparation=0 裁决失败
        adv = c.post(f"/api/v1/lives/{life_id}/advance", json={"delta": 8 * 86400})
        assert adv.status_code == 200
        world = c.get(f"/api/v1/lives/{life_id}/world").json()["data"]
        assert world["facts"]["presentation_done"] is True
        assert world["facts"]["presentation_success"] is False


def test_advance_fires_chronicle_milestone():
    with _client() as c:
        life_id = _create_life(c, scenario="chronicle")
        world0 = c.get(f"/api/v1/lives/{life_id}/world").json()["data"]
        assert world0["scenario_type"] == "chronicle"
        assert "chronicle" in world0
        assert world0["death_info"]["alive"] is True
        # 推进 6 年 → 6 岁「入学」里程碑（§12E §21-24）
        c.post(f"/api/v1/lives/{life_id}/advance", json={"delta": 6 * 365 * 86400})
        world = c.get(f"/api/v1/lives/{life_id}/world").json()["data"]
        assert any("入学" in line for line in world["chronicle"])
        assert world["death_info"]["alive"] is True


def test_delete_life_removes_scenario():
    with _client() as c:
        life_id = _create_life(c, scenario="presentation")
        assert c.delete(f"/api/v1/lives/{life_id}").status_code == 204
        assert c.get(f"/api/v1/lives/{life_id}").status_code == 404
