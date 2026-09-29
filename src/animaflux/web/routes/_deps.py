"""路由共享依赖（§Web Plan §9 / §13）。

统一「FastAPI Route → SessionRegistry → LifeSession → acquire lock → LifeHandle public method」的
取会话路径，并集中 request_id 提取。所有操作只走 Public Facade，不穿透 Core。
"""

from __future__ import annotations

from fastapi import Request

from animaflux.web.errors import branch_not_found, life_not_found


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_session(request: Request, life_id: str, branch_id: str = "main"):
    """取 (life_id, branch_id) 的 LifeSession；life 不存在或 branch 未物化时抛稳定 WebError。"""
    flux = request.app.state.flux
    if life_id not in flux.list_lives():
        raise life_not_found(life_id)
    try:
        return request.app.state.registry.get(life_id, branch_id)
    except KeyError:
        raise branch_not_found(branch_id)
