"""FastAPI 应用工厂（§Web Plan §2 / §39.1 / §39.22 / §18 / §19 / §21）。

Web 是 Public API 的消费者；核心对它 zero import fastapi / uvicorn。API 前缀 /api/v1，健康检查
/api/health，静态前端挂 /。本地单用户（127.0.0.1，workers=1）——无 auth、无复杂 CORS（§20/§21）。

后端 / LLM 均经 `AnimaFlux.from_config(...)` 装配（§39.20），Web 不 import SQLite 仓库内部，
也不直接 import LLM Provider（§Web Plan §2/§10）。
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from animaflux.api import AnimaFlux
from animaflux.web.config import WebSettings
from animaflux.web.dto import envelope_err
from animaflux.web.errors import WebError
from animaflux.web.routes import branches, diary, history, interaction, lives, state
from animaflux.web.scenarios import ScenarioRegistry
from animaflux.web.sessions import SessionRegistry

_STATIC_DIR = Path(__file__).parent / "static"
_DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def _build_config(settings: WebSettings) -> dict:
    """装配 AnimaFlux 配置：SQLite 后端 + 可选 LLM capability（§15D / §39.20）。

    未配置 API key 则确定性运行（Deterministic First）。
    """
    config: dict = {"backend": {"type": "sqlite", "path": settings.db_path}}
    if os.environ.get("ANIMAFLUX_SILICONFLOW_API_KEY"):
        config["llm"] = {
            "provider": "siliconflow",
            "model": os.environ.get("ANIMAFLUX_LLM_MODEL", _DEFAULT_MODEL),
        }
    return config


def create_app(settings: WebSettings | None = None) -> FastAPI:
    settings = settings or WebSettings.from_env()
    flux = AnimaFlux.from_config(_build_config(settings))
    scenarios = ScenarioRegistry()
    registry = SessionRegistry(flux, scenarios=scenarios)

    app = FastAPI(
        title="AnimaFlux Local Web Console",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.flux = flux
    app.state.registry = registry
    app.state.scenarios = scenarios
    app.state.settings = settings

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(WebError)
    async def web_error_handler(request: Request, exc: WebError):
        return JSONResponse(
            status_code=exc.http_status,
            content=envelope_err(exc.code, exc.message, request_id=getattr(request.state, "request_id", None)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=envelope_err("VALIDATION_ERROR", "invalid request body", request_id=getattr(request.state, "request_id", None)),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=envelope_err("INTERNAL_ERROR", "internal server error", request_id=getattr(request.state, "request_id", None)),
        )

    app.include_router(lives.router, prefix="/api/v1")
    app.include_router(interaction.router, prefix="/api/v1")
    app.include_router(state.router, prefix="/api/v1")
    app.include_router(history.router, prefix="/api/v1")
    app.include_router(branches.router, prefix="/api/v1")
    app.include_router(diary.router, prefix="/api/v1")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
