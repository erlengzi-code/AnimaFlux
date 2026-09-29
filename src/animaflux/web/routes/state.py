"""State Inspection 路由（§Web Plan §12.4 / §39.14 / §39.15）。

`GET /states` 返回 13 个 Core State 的轻量概览（namespace + 展示名 + seeded + version），
`GET /states/{namespace}` 返回单个 Namespace 的完整只读 View（未 seed 返回 seeded=false）。
前端据此渲染 Mind 页面；未知 Namespace 走 Generic Renderer（§39.15）。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from animaflux.web.dto import envelope_ok
from animaflux.web.errors import namespace_not_found
from animaflux.web.routes._deps import get_session, request_id

router = APIRouter(tags=["state"])

_DISPLAY_NAMES = {
    "identity": "身份 Identity",
    "body": "身体 Body",
    "personality": "人格 Personality",
    "emotion": "情绪 Emotion",
    "drive": "驱力 Drive",
    "memory": "记忆 Memory",
    "belief": "信念 Belief",
    "value": "价值 Value",
    "goal": "目标 Goal",
    "relationship": "关系 Relationship",
    "world_model": "世界模型 World Model",
    "self_model": "自我模型 Self Model",
    "narrative": "叙事 Narrative",
}


@router.get("/lives/{life_id}/states")
def list_states(life_id: str, request: Request):
    session = get_session(request, life_id)
    # 13 个 Core State 的枚举顺序来自 Public Facade 的 state_overview()（§39.14），
    # Web 不 import StateNamespace 契约（§Web Plan §2）。
    data = [
        {
            "namespace": s["namespace"],
            "display_name": _DISPLAY_NAMES.get(s["namespace"], s["namespace"]),
            "seeded": s["seeded"],
            "version": s["version"],
        }
        for s in session.handle.state_overview()
    ]
    return envelope_ok(data, request_id=request_id(request))


@router.get("/lives/{life_id}/states/{namespace}")
def get_state(life_id: str, namespace: str, request: Request):
    session = get_session(request, life_id)
    try:
        view = session.handle.inspect_named(namespace)
    except ValueError:
        raise namespace_not_found(namespace)
    if view is None:
        return envelope_ok(
            {"namespace": namespace, "seeded": False, "version": None, "data": None},
            request_id=request_id(request),
        )
    return envelope_ok(
        {
            "namespace": view.namespace.value,
            "seeded": True,
            "version": view.version,
            "data": view.data,
        },
        request_id=request_id(request),
    )
