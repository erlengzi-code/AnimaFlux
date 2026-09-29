"""Branch 路由（§Web Plan §12.9 / §13 / §33 / §39.12）。

Checkpoint ≠ Branch（§14）：先 checkpoint 再 branch；这里提供 list / create / snapshot（compare）。
v0.1 Branch 为进程内 Fork（LifeBranchHandle），只读快照比较，不提供分支内人类交互 step（待后续）。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from animaflux.web.dto import envelope_ok
from animaflux.web.errors import branch_not_found, checkpoint_not_found
from animaflux.web.routes._deps import get_session, request_id

router = APIRouter(tags=["branches"])


class CreateBranchRequest(BaseModel):
    name: str = "branch"
    checkpoint_id: str | None = None


@router.get("/lives/{life_id}/branches")
def list_branches(life_id: str, request: Request):
    session = get_session(request, life_id)
    return envelope_ok(session.handle.list_branches(), request_id=request_id(request))


@router.post("/lives/{life_id}/branches", status_code=201)
def create_branch(life_id: str, req: CreateBranchRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        try:
            handle = session.handle.branch(name=req.name, checkpoint_id=req.checkpoint_id)
        except KeyError:
            raise checkpoint_not_found(req.checkpoint_id or "")
    return envelope_ok(handle.record, request_id=request_id(request))


@router.get("/lives/{life_id}/branches/{branch_id}")
def get_branch(life_id: str, branch_id: str, request: Request):
    session = get_session(request, life_id)
    try:
        handle = session.handle.get_branch(branch_id)
    except KeyError:
        raise branch_not_found(branch_id)
    return envelope_ok(handle.record, request_id=request_id(request))


@router.get("/lives/{life_id}/branches/{branch_id}/snapshot")
def branch_snapshot(life_id: str, branch_id: str, request: Request):
    session = get_session(request, life_id)
    try:
        handle = session.handle.get_branch(branch_id)
    except KeyError:
        raise branch_not_found(branch_id)
    return envelope_ok(handle.snapshot(), request_id=request_id(request))
