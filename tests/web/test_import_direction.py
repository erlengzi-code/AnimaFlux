"""Web import-direction Contract Tests（§Web Plan §2 / §10）。

把「Web 是 Public API 的消费者；Core 对它 zero import fastapi/uvicorn」翻译成会失败的测试：
  1. 冻结 Core（非 web/）不得 import fastapi / uvicorn；
  2. web/ 只允许 import `animaflux.api`（Public Facade）与 `animaflux.web.*`，
     不得穿透 StateStore / Resolver / Transaction / SQLite 仓库 / PluginManager / LLM Provider。
"""

from __future__ import annotations

import ast
from pathlib import Path

import animaflux

PKG_ROOT = Path(animaflux.__file__).parent
WEB_DIR = PKG_ROOT / "web"

_CORE_FORBIDDEN = {"fastapi", "uvicorn"}


def _py_files(root: Path):
    return sorted(root.rglob("*.py"))


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


def test_core_imports_zero_fastapi_or_uvicorn():
    offenders: dict[str, set[str]] = {}
    for py in _py_files(PKG_ROOT):
        if WEB_DIR in py.parents:
            continue
        for mod in _imported_modules(py):
            if mod.split(".")[0] in _CORE_FORBIDDEN:
                offenders.setdefault(str(py.relative_to(PKG_ROOT.parent)), set()).add(mod)
    assert not offenders, f"冻结 Core 引入 FastAPI/Uvicorn 依赖：{offenders}"


def test_web_imports_only_public_api_and_web():
    offenders: dict[str, set[str]] = {}
    for py in _py_files(WEB_DIR):
        for mod in _imported_modules(py):
            if not mod.startswith("animaflux"):
                continue
            if mod == "animaflux" or mod == "animaflux.api" or mod.startswith("animaflux.web"):
                continue
            offenders.setdefault(str(py.relative_to(PKG_ROOT.parent)), set()).add(mod)
    assert not offenders, f"Web 穿透 Public Facade，import 了核心内部：{offenders}"
