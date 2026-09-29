"""Diary 路由（§13M）：Narrative 的对外呈现。

GET 列出日记（新在前）；POST 点击写一篇（话题 / 时间段可选）。只经 Public Facade
（LifeHandle.diary / write_diary），不穿透 Core；无 world 的生命也能写（日记不依赖环境）。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from animaflux.web.dto import envelope_ok
from animaflux.web.routes._deps import get_session, request_id

router = APIRouter(tags=["diary"])


class WriteDiaryRequest(BaseModel):
    topic: str | None = None
    time_start: str | None = None
    time_end: str | None = None


@router.get("/lives/{life_id}/diary")
def list_diary(life_id: str, request: Request):
    session = get_session(request, life_id)
    return envelope_ok(list(session.handle.diary()), request_id=request_id(request))


@router.post("/lives/{life_id}/diary", status_code=201)
def write_diary(life_id: str, req: WriteDiaryRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        entry = session.handle.write_diary(
            topic=req.topic,
            time_start=req.time_start,
            time_end=req.time_end,
        )
    return envelope_ok(entry, request_id=request_id(request))
