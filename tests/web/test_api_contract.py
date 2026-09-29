"""Web API Contract Tests（§Web Plan §12.1 / §16 / §17 / §39.27）。

用 FastAPI TestClient 验证 REST 契约：envelope 形状、health、lives CRUD、错误映射、静态托管。
全部走 `create_app(WebSettings(db_path=":memory:"))`，不触碰真实 SQLite 文件。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from animaflux.web.app import create_app
from animaflux.web.config import WebSettings


def _client():
    return TestClient(create_app(WebSettings(db_path=":memory:")))


def test_health():
    with _client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_list_lives_empty():
    with _client() as c:
        resp = c.get("/api/v1/lives")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["request_id"]
        assert resp.headers.get("x-request-id") == body["meta"]["request_id"]


def test_list_lives_survives_partial_life():
    """一条半 seed 的残损生命不应拖垮整个列表，仍可被删除（§Web Plan §10）。"""
    with _client() as c:
        flux = c.app.state.flux
        flux.create_life("partial-life")
        # 模拟历史遗留：删掉 drive 的 current 指针 → summary 会 KeyError
        flux.backend._conn.execute(
            "DELETE FROM state_current WHERE agent_id = ? AND namespace = ?",
            ("partial-life", "drive"),
        )

        resp = c.get("/api/v1/lives")
        assert resp.status_code == 200
        data = resp.json()["data"]
        entry = next(x for x in data if x["life_id"] == "partial-life")
        assert entry["vital_status"] == "BROKEN"

        # 残损生命可通过 DELETE 清除
        assert c.delete("/api/v1/lives/partial-life").status_code == 204
        assert c.get("/api/v1/lives/partial-life").status_code == 404


def test_create_and_get_life():
    with _client() as c:
        resp = c.post("/api/v1/lives", json={"primary_name": "小明", "values": ["growth"]})
        assert resp.status_code == 201
        created = resp.json()["data"]
        assert created["primary_name"] == "小明"
        assert "growth" in created["top_values"]
        assert created["vital_status"]
        life_id = created["life_id"]

        # 列表包含新生命
        listing = c.get("/api/v1/lives").json()["data"]
        assert [l["life_id"] for l in listing] == [life_id]

        # 单生命 summary
        one = c.get(f"/api/v1/lives/{life_id}").json()["data"]
        assert one["life_id"] == life_id
        assert one["primary_name"] == "小明"


def test_get_life_not_found():
    with _client() as c:
        resp = c.get("/api/v1/lives/nope")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "LIFE_NOT_FOUND"
        assert body["meta"]["request_id"]


def test_create_ignores_client_life_id_and_generates_unique_ids():
    """life_id 不接受客户端填写：同名/同 id 请求仍各自生成唯一 ID（§Web Plan §10）。"""
    with _client() as c:
        a = c.post("/api/v1/lives", json={"life_id": "dup", "primary_name": "A"})
        b = c.post("/api/v1/lives", json={"life_id": "dup", "primary_name": "B"})
        assert a.status_code == 201
        assert b.status_code == 201
        id_a = a.json()["data"]["life_id"]
        id_b = b.json()["data"]["life_id"]
        assert id_a != id_b
        assert id_a != "dup" and id_b != "dup"
        listing = c.get("/api/v1/lives").json()["data"]
        assert {l["life_id"] for l in listing} == {id_a, id_b}


def test_invalid_body_is_422():
    with _client() as c:
        resp = c.post("/api/v1/lives", json={"primary_name": 12345})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_static_frontend_served():
    with _client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert "AnimaFlux" in resp.text
