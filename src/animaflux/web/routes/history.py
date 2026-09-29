"""History / Timeline / Checkpoint / Development / Memory 路由（§Web Plan §12.5–§12.8）。

全部只读或经 Public Facade：Timeline 走 Replay（§21.3 只读），Checkpoint 走 LifeHandle.checkpoint()，
Development 走 DevelopmentContextBuilder 派生的 View（§24.14）。不直接解析 Commit Journal / DB。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from animaflux.web.dto import envelope_ok
from animaflux.web.errors import checkpoint_not_found
from animaflux.web.routes._deps import get_session, request_id

router = APIRouter(tags=["history"])


def _checkpoint_dict(cp) -> dict:
    return {
        "checkpoint_id": cp.checkpoint_id,
        "agent_id": cp.agent_id,
        "fork_world_time": cp.fork_world_time,
        "namespaces": sorted(cp.version_map.keys()),
    }


@router.get("/lives/{life_id}/timeline")
def timeline(life_id: str, request: Request):
    session = get_session(request, life_id)
    return envelope_ok(session.handle.timeline(), request_id=request_id(request))


@router.get("/lives/{life_id}/agency")
def agency(life_id: str, request: Request):
    """主动决策的「为什么」叙事（§12E A8）：运行时内存，只读。"""
    session = get_session(request, life_id)
    return envelope_ok(list(session.handle.agency_log()), request_id=request_id(request))


@router.get("/lives/{life_id}/development")
def development(life_id: str, request: Request):
    session = get_session(request, life_id)
    return envelope_ok(session.handle.development(), request_id=request_id(request))


@router.get("/lives/{life_id}/memories")
def memories(life_id: str, request: Request):
    session = get_session(request, life_id)
    return envelope_ok(list(session.handle.memories()), request_id=request_id(request))


@router.get("/lives/{life_id}/checkpoints")
def list_checkpoints(life_id: str, request: Request):
    session = get_session(request, life_id)
    data = [_checkpoint_dict(cp) for cp in session.handle.list_checkpoints()]
    return envelope_ok(data, request_id=request_id(request))


@router.post("/lives/{life_id}/checkpoints", status_code=201)
def create_checkpoint(life_id: str, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        cp = session.handle.checkpoint()
    return envelope_ok(_checkpoint_dict(cp), request_id=request_id(request))


class RestoreRequest(BaseModel):
    checkpoint_id: str


@router.post("/lives/{life_id}/restore")
def restore_life(life_id: str, req: RestoreRequest, request: Request):
    """RESTORE（§39.10）：从指定 Checkpoint 延续原生命，走 Public Restore API（§21.4）。

    v0.1 Restore 用独立 InMemory 后端承载新 Runtime，替换当前 LifeHandle（不修改 current
    pointer / 数据库记录）。返回恢复后的 Life Summary。
    """
    session = get_session(request, life_id)
    with session.lock:
        try:
            restored = session.handle.restore_checkpoint(req.checkpoint_id)
        except KeyError:
            raise checkpoint_not_found(req.checkpoint_id)
    session.handle = restored
    return envelope_ok(restored.summary(), request_id=request_id(request))
