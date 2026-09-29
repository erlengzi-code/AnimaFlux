"""Life 资源路由（§Web Plan §12.1 / §39.1 / §39.7）。

GET  /api/v1/lives          list lives
POST /api/v1/lives          create life
GET  /api/v1/lives/{id}     life summary

只走 Public Facade（AnimaFlux.list_lives / create_life / LifeHandle.summary），不穿透 Core。
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from animaflux.api import AnimaFlux, CharacterBootstrap, _WORLD_EPOCH, build_scenario_environment
from animaflux.web.dto import envelope_ok, to_jsonable
from animaflux.web.errors import life_not_found

router = APIRouter(tags=["lives"])


class CreateLifeRequest(BaseModel):
    """创建生命请求体（§39.7 Basic Form 最小集）。Web 只负责表单与 DTO，不推导人格/信念/价值。

    life_id 不接受客户端填写：由服务端随机生成（§Web Plan §10），避免 ID 冲突与可预测性。
    `scenario` 可选：none（无世界）/ presentation（多日演讲）/ chronicle（完整一生），§12E。
    """

    primary_name: str = "小林"
    birth_time: datetime | None = None
    values: list[str] = []
    traits: dict[str, float] | None = None
    scenario: str = "none"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _generate_life_id(primary_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", primary_name).strip("-").lower() or "life"
    return f"{slug}-{uuid4().hex[:6]}"


def _summary_payload(handle, scenarios, life_id: str) -> dict:
    """LifeSummaryView + scenario_type（§12E）：world 类型从进程内注册表取，供前端打场景 pill。"""
    payload = to_jsonable(handle.summary())
    payload["scenario_type"] = scenarios.get(life_id)[1]
    return payload


@router.get("/lives")
def list_lives(request: Request):
    flux: AnimaFlux = request.app.state.flux
    lives = []
    for life_id in flux.list_lives():
        session = request.app.state.registry.get(life_id)
        try:
            lives.append(_summary_payload(session.handle, request.app.state.scenarios, life_id))
        except Exception:
            # 半 seed 的残损生命（历史遗留 bug 的产物）不应拖垮整个列表；
            # 以 BROKEN 占位呈现，仍可通过 DELETE 删除。
            lives.append({"life_id": life_id, "primary_name": life_id, "vital_status": "BROKEN"})
    return envelope_ok(lives, request_id=_request_id(request))


@router.post("/lives", status_code=201)
def create_life(req: CreateLifeRequest, request: Request):
    flux: AnimaFlux = request.app.state.flux
    life_id = _generate_life_id(req.primary_name)
    while life_id in flux.list_lives():
        life_id = _generate_life_id(req.primary_name)

    env, scenario_type = build_scenario_environment(req.scenario)
    # 场景生命的世界锚点对齐（§12E）：把 identity.birth_time 对齐到 _WORLD_EPOCH，使生命自己的
    # chronological_age 与世界压缩年龄一致（否则默认 1980 会导致「20 岁 vs 0 岁」错位）。
    birth_time = req.birth_time
    if scenario_type is not None and birth_time is None:
        birth_time = _WORLD_EPOCH
    bootstrap = CharacterBootstrap(
        primary_name=req.primary_name,
        birth_time=birth_time,
        traits=req.traits,
        values=tuple(req.values),
    )
    handle = flux.create_life(life_id, bootstrap=bootstrap, environment=env)
    request.app.state.scenarios.register(life_id, env, scenario_type)
    # 完整一生从「出生」开始：喂第一条出生感知（中性，不携带评价触发词）。
    if scenario_type == "chronicle":
        handle.step(0.0, observations=(env.birth_observation(),))
    return envelope_ok(_summary_payload(handle, request.app.state.scenarios, life_id), request_id=_request_id(request))


@router.delete("/lives/{life_id}", status_code=204)
def delete_life(life_id: str, request: Request):
    flux: AnimaFlux = request.app.state.flux
    if life_id not in flux.list_lives():
        raise life_not_found(life_id)
    request.app.state.registry.remove(life_id)
    request.app.state.scenarios.remove(life_id)
    flux.delete_life(life_id)
    return Response(status_code=204)


@router.get("/lives/{life_id}")
def get_life(life_id: str, request: Request):
    flux: AnimaFlux = request.app.state.flux
    if life_id not in flux.list_lives():
        raise life_not_found(life_id)
    session = request.app.state.registry.get(life_id)
    return envelope_ok(_summary_payload(session.handle, request.app.state.scenarios, life_id), request_id=_request_id(request))
