"""Web 配置（§Web Plan §5 / §39.20）。

从环境变量读取，不引入 pydantic-settings（保持 Web 依赖最小）。默认本地 127.0.0.1 / 8000 /
SQLite 文件 `animaflux.db`。Web 不建设独立 Settings 系统，LLM 配置复用 AnimaFlux.from_config
路径（此处仅暴露 host/port/db）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_DB_PATH = "animaflux.db"


@dataclass(frozen=True)
class WebSettings:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    db_path: str = DEFAULT_DB_PATH

    @classmethod
    def from_env(cls) -> "WebSettings":
        return cls(
            host=os.environ.get("ANIMAFLUX_HOST", DEFAULT_HOST),
            port=int(os.environ.get("ANIMAFLUX_PORT", str(DEFAULT_PORT))),
            db_path=os.environ.get("ANIMAFLUX_DB", DEFAULT_DB_PATH),
        )
