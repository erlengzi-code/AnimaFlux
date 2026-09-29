"""Runtime / Interaction 路由（§Web Plan §12.2 / §12.3 / §28）。

step / advance / observe / say —— 全部经 LifeSession lock 串行（§8），再调 LifeHandle 公开方法。
`say` 返回结构化 TurnResult（含 tick_id / trace_ref，供 Talk「Why」抽屉使用）。
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Request
from pydantic import BaseModel

from animaflux.web.dto import envelope_ok
from animaflux.web.errors import no_world, validation_error
from animaflux.web.routes._deps import get_session, request_id

router = APIRouter(tags=["interaction"])

_UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(d|h|m|s)")


def parse_delta(value) -> float:
    """把 delta 解析成秒。支持数字（秒）与时长字符串（"1d" / "2h" / "30m" / "1d6h"）。"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        compact = "".join(value.split()).lower()
        if not compact:
            return 0.0
        if _DURATION_RE.search(compact):
            total = 0.0
            pos = 0
            for m in _DURATION_RE.finditer(compact):
                if m.start() != pos:
                    raise validation_error(f"invalid delta: {value!r}")
                total += float(m.group(1)) * _UNITS[m.group(2)]
                pos = m.end()
            if pos != len(compact):
                raise validation_error(f"invalid delta: {value!r}")
            return total
        try:
            return float(compact)
        except ValueError:
            raise validation_error(f"invalid delta: {value!r}")
    raise validation_error("invalid delta")


class StepRequest(BaseModel):
    delta: str | float = 60.0


class ObserveRequest(BaseModel):
    content: str


class SayRequest(BaseModel):
    text: str


@router.post("/lives/{life_id}/step")
def step_life(life_id: str, req: StepRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        tick_id = session.handle.step(parse_delta(req.delta))
    return envelope_ok({"tick_id": tick_id}, request_id=request_id(request))


@router.post("/lives/{life_id}/advance")
def advance_life(life_id: str, req: StepRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        # 有世界时把「推进后到期」的排程事件一并回灌（单 Tick，§12E）；无世界退化为纯推进。
        tick_id = session.handle.advance_world(parse_delta(req.delta))
    return envelope_ok({"tick_id": tick_id}, request_id=request_id(request))


@router.post("/lives/{life_id}/act")
def act_life(life_id: str, request: Request):
    """一次主动决策机会（§12E）：Internal Motivation → Decision → Action → World → 回灌。

    无 world 的生命（scenario=none）返回 NO_WORLD；NO_ACTION 时只回 acted=False + 理由。
    """
    session = get_session(request, life_id)
    with session.lock:
        try:
            outcome = session.handle.act()
        except RuntimeError:
            raise no_world(life_id)

    result: dict = {"acted": outcome.acted}
    if outcome.decision is not None:
        result["no_action_reason"] = outcome.decision.no_action_reason
        result["confidence"] = outcome.decision.confidence
    if outcome.intent is not None:
        result["action_type"] = outcome.intent.action_type
        result["expected_outcome"] = outcome.intent.expected_outcome
    if outcome.tick_id is not None:
        result["tick_id"] = outcome.tick_id
    if outcome.action_result is not None:
        result["status"] = outcome.action_result.status
        result["consequence"] = outcome.action_result.consequence
        if outcome.action_result.observations:
            result["observation"] = outcome.action_result.observations[0].content
    return envelope_ok(result, request_id=request_id(request))


@router.get("/lives/{life_id}/world")
def world_view(life_id: str, request: Request):
    """只读世界事实（§12E）：外部世界事实，非 Core State；无 world 时 scenario_type=None。"""
    session = get_session(request, life_id)
    _env, scenario_type = request.app.state.scenarios.get(life_id)
    view = session.handle.world_view()
    if view is None:
        return envelope_ok(
            {"scenario_type": None, "facts": {}}, request_id=request_id(request)
        )
    view["scenario_type"] = scenario_type
    return envelope_ok(view, request_id=request_id(request))


@router.post("/lives/{life_id}/observe")
def observe_life(life_id: str, req: ObserveRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        tick_id = session.handle.observe_text(req.content)
    return envelope_ok({"tick_id": tick_id}, request_id=request_id(request))


@router.post("/lives/{life_id}/say")
def say_to_life(life_id: str, req: SayRequest, request: Request):
    session = get_session(request, life_id)
    with session.lock:
        result = session.handle.send_text(req.text)
    return envelope_ok(result, request_id=request_id(request))
