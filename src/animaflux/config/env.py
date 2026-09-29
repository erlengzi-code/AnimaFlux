"""最小 .env 加载器（v5.9 §16C / Web Plan §6）。

v0.1 冻结铁律「依赖最小化」，不引入 python-dotenv 第三方库，用标准库实现一个
满足「不覆盖已存在环境变量」约定的极简 loader。用途：让 LLM Provider 的 API Key
可以从 `.env` 读取，避免把密钥硬编码进源码或命令行（见 CLAUDE.md「LLM 策略」）。

语法最简：`KEY=VALUE`，支持空行、`#` 整行注释、双/单引号包裹的值。不展开 `$VAR`、
不支持内联注释（值里含 `#` 时按原样保留）。
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(
    path: str | os.PathLike[str] | None = None,
    *,
    override: bool = False,
) -> dict[str, str]:
    """解析 .env 并把未在 os.environ 里的键写入，返回成功解析的 {key: value}。

    - 默认 `.env` 位于当前工作目录；可用环境变量 ``ANIMAFLUX_DOTENV`` 指定显式路径，
      或直接传 ``path``。
    - 默认不覆盖已存在的环境变量（标准 dotenv 约定）；``override=True`` 强制覆盖。
    """
    if path is None:
        path = os.environ.get("ANIMAFLUX_DOTENV", ".env")
    dotenv_path = Path(path)
    if not dotenv_path.is_file():
        return {}

    parsed: dict[str, str] = {}
    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        parsed[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return parsed


__all__ = ["load_dotenv"]
