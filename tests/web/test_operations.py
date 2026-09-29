"""W1 Operations Tests（§Web Plan §12.2–§12.9）。

覆盖 Runtime/Interaction（step/advance/observe/say）、State Inspection、History（timeline /
development / memories / checkpoints）、Branch（list/create/get/snapshot）。全部走 in-memory SQLite
（db_path=":memory:"），不触碰真实文件；验证 envelope 形状与数据流（不穿透 Core）。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from animaflux.web.app import create_app
from animaflux.web.config import WebSettings


def _client():
    return TestClient(create_app(WebSettings(db_path=":memory:")))


def _create_life(c) -> str:
    resp = c.post("/api/v1/lives", json={"primary_name": "小林", "values": ["growth"]})
    assert resp.status_code == 201
    return resp.json()["data"]["life_id"]


def test_step_and_advance():
    with _client() as c:
        life_id = _create_life(c)
        step = c.post(f"/api/v1/lives/{life_id}/step", json={"delta": 60})
        assert step.status_code == 200
        assert step.json()["data"]["tick_id"]

        adv = c.post(f"/api/v1/lives/{life_id}/advance", json={"delta": "1d6h"})
        assert adv.status_code == 200
        assert adv.json()["data"]["tick_id"]


def test_advance_invalid_delta_is_422():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.post(f"/api/v1/lives/{life_id}/advance", json={"delta": "banana"})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_observe_and_say():
    with _client() as c:
        life_id = _create_life(c)
        obs = c.post(f"/api/v1/lives/{life_id}/observe", json={"content": "外面下雨了"})
        assert obs.status_code == 200
        assert obs.json()["data"]["tick_id"]

        said = c.post(f"/api/v1/lives/{life_id}/say", json={"text": "我有点害怕"})
        assert said.status_code == 200
        turn = said.json()["data"]
        assert isinstance(turn["text"], str) and turn["text"]
        assert turn["tick_id"]
        assert "trace_ref" in turn


def test_states_overview_has_13_with_12_seeded():
    with _client() as c:
        life_id = _create_life(c)
        data = c.get(f"/api/v1/lives/{life_id}/states").json()["data"]
        assert len(data) == 13
        seeded = [s for s in data if s["seeded"]]
        assert len(seeded) == 12
        assert all("display_name" in s and "namespace" in s for s in data)


def test_get_seeded_and_unseeded_state():
    with _client() as c:
        life_id = _create_life(c)
        ident = c.get(f"/api/v1/lives/{life_id}/states/identity").json()["data"]
        assert ident["seeded"] is True
        assert ident["data"]["primary_name"] == "小林"

        memory = c.get(f"/api/v1/lives/{life_id}/states/memory").json()["data"]
        assert memory["seeded"] is False
        assert memory["data"] is None


def test_get_unknown_namespace_is_404():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.get(f"/api/v1/lives/{life_id}/states/nope")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NAMESPACE_NOT_FOUND"


def test_timeline_grows_after_step():
    with _client() as c:
        life_id = _create_life(c)
        c.post(f"/api/v1/lives/{life_id}/step", json={"delta": 60})
        c.post(f"/api/v1/lives/{life_id}/observe", json={"content": "hello"})
        ticks = c.get(f"/api/v1/lives/{life_id}/timeline").json()["data"]
        assert len(ticks) >= 1
        for t in ticks:
            assert "tick_id" in t and "commit_id" in t
            assert isinstance(t["payloads"], dict)


def test_development_context():
    with _client() as c:
        life_id = _create_life(c)
        dev = c.get(f"/api/v1/lives/{life_id}/development").json()["data"]
        assert dev["agent_id"] == life_id
        assert isinstance(dev["life_stage"], str)
        assert isinstance(dev["role_refs"], list)


def test_memories_empty_on_new_life():
    with _client() as c:
        life_id = _create_life(c)
        assert c.get(f"/api/v1/lives/{life_id}/memories").json()["data"] == []


def test_memories_form_after_interaction():
    with _client() as c:
        life_id = _create_life(c)
        # 显著事件 → Memory Formation（§13F.6）
        c.post(f"/api/v1/lives/{life_id}/observe", json={"content": "外面下雨了"})
        c.post(f"/api/v1/lives/{life_id}/say", json={"text": "我有点害怕"})
        data = c.get(f"/api/v1/lives/{life_id}/memories").json()["data"]
        assert isinstance(data, list) and data
        for m in data:
            assert "memory_id" in m and "memory_type" in m
            assert "importance" in m and "emotional_salience" in m
            assert "accessibility" in m and "retrieval_count" in m


def test_checkpoint_create_and_list():
    with _client() as c:
        life_id = _create_life(c)
        assert c.get(f"/api/v1/lives/{life_id}/checkpoints").json()["data"] == []
        resp = c.post(f"/api/v1/lives/{life_id}/checkpoints")
        assert resp.status_code == 201
        cp = resp.json()["data"]
        assert cp["checkpoint_id"] and cp["agent_id"] == life_id
        assert isinstance(cp["namespaces"], list)
        listed = c.get(f"/api/v1/lives/{life_id}/checkpoints").json()["data"]
        assert [x["checkpoint_id"] for x in listed] == [cp["checkpoint_id"]]


def test_branch_lifecycle_and_snapshot():
    with _client() as c:
        life_id = _create_life(c)
        assert c.get(f"/api/v1/lives/{life_id}/branches").json()["data"] == []

        created = c.post(f"/api/v1/lives/{life_id}/branches", json={"name": "alt"})
        assert created.status_code == 201
        rec = created.json()["data"]
        assert rec["branch_name"] == "alt"
        assert rec["parent_branch_id"] == "main"
        assert rec["branch_id"]

        listed = c.get(f"/api/v1/lives/{life_id}/branches").json()["data"]
        assert [b["branch_id"] for b in listed] == [rec["branch_id"]]

        one = c.get(f"/api/v1/lives/{life_id}/branches/{rec['branch_id']}").json()["data"]
        assert one["branch_id"] == rec["branch_id"]

        snap = c.get(f"/api/v1/lives/{life_id}/branches/{rec['branch_id']}/snapshot").json()["data"]
        assert isinstance(snap, dict)
        assert "identity" in snap


def test_branch_not_found_is_404():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.get(f"/api/v1/lives/{life_id}/branches/nope")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "BRANCH_NOT_FOUND"


def test_branch_from_specific_checkpoint():
    with _client() as c:
        life_id = _create_life(c)
        cp = c.post(f"/api/v1/lives/{life_id}/checkpoints").json()["data"]
        resp = c.post(
            f"/api/v1/lives/{life_id}/branches",
            json={"name": "alt", "checkpoint_id": cp["checkpoint_id"]},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["fork_checkpoint_id"] == cp["checkpoint_id"]


def test_branch_unknown_checkpoint_is_404():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.post(f"/api/v1/lives/{life_id}/branches", json={"name": "x", "checkpoint_id": "nope"})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CHECKPOINT_NOT_FOUND"


def test_restore_from_checkpoint():
    with _client() as c:
        life_id = _create_life(c)
        c.post(f"/api/v1/lives/{life_id}/step", json={"delta": 60})
        cp = c.post(f"/api/v1/lives/{life_id}/checkpoints").json()["data"]
        c.post(f"/api/v1/lives/{life_id}/step", json={"delta": 60})

        resp = c.post(f"/api/v1/lives/{life_id}/restore", json={"checkpoint_id": cp["checkpoint_id"]})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["life_id"] == life_id
        assert data["primary_name"] == "小林"
        # 恢复后进程内 Checkpoint 列表重置（新 Runtime 快照延续）
        assert c.get(f"/api/v1/lives/{life_id}/checkpoints").json()["data"] == []


def test_restore_unknown_checkpoint_is_404():
    with _client() as c:
        life_id = _create_life(c)
        resp = c.post(f"/api/v1/lives/{life_id}/restore", json={"checkpoint_id": "nope"})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CHECKPOINT_NOT_FOUND"


def test_create_life_id_is_auto_generated():
    with _client() as c:
        # 客户端传 life_id 也不被采用，服务端总是随机生成（§Web Plan §10）
        resp = c.post("/api/v1/lives", json={"primary_name": "小林", "life_id": "should-be-ignored"})
        assert resp.status_code == 201
        lid = resp.json()["data"]["life_id"]
        assert lid != "should-be-ignored"
        assert lid.startswith("life-")  # slug("小林") → "life"


def test_delete_life():
    with _client() as c:
        life_id = _create_life(c)
        ids = lambda: [l["life_id"] for l in c.get("/api/v1/lives").json()["data"]]
        assert life_id in ids()

        resp = c.delete(f"/api/v1/lives/{life_id}")
        assert resp.status_code == 204
        assert life_id not in ids()
        assert c.get(f"/api/v1/lives/{life_id}").status_code == 404


def test_delete_unknown_life_is_404():
    with _client() as c:
        assert c.delete("/api/v1/lives/nope").status_code == 404
