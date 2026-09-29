"""config/env.py 的 .env loader 测试（v5.9 §15C.11：密钥不硬编码，从 .env 读取）。"""

from __future__ import annotations

import os

from animaflux.config.env import load_dotenv
from animaflux.llm.providers import SiliconFlowProvider


def _write(tmp_path, content):
    dotenv = tmp_path / ".env"
    dotenv.write_text(content, encoding="utf-8")
    return dotenv


def test_load_dotenv_parses_and_skips_comments(tmp_path):
    dotenv = _write(
        tmp_path,
        "# 整行注释\n\nP1_A=value1\nP1_B=\"quoted\"\nP1_C='single'\nNO_SEP_this_line\n",
    )
    parsed = load_dotenv(dotenv)
    assert parsed == {"P1_A": "value1", "P1_B": "quoted", "P1_C": "single"}
    assert os.environ["P1_A"] == "value1"


def test_load_dotenv_does_not_override_existing_env(monkeypatch, tmp_path):
    dotenv = _write(tmp_path, "P2_EXISTING=from-dotenv\nP2_NEW=new\n")
    monkeypatch.setenv("P2_EXISTING", "already-exported")
    load_dotenv(dotenv)
    # 已 export 的变量不被 .env 覆盖（标准 dotenv 约定）；未设置的才写入
    assert os.environ["P2_EXISTING"] == "already-exported"
    assert os.environ["P2_NEW"] == "new"


def test_load_dotenv_missing_file_returns_empty():
    assert load_dotenv("__no_such_dotenv_file__.env") == {}


def test_provider_reads_key_from_dotenv(monkeypatch, tmp_path):
    _write(tmp_path, "ANIMAFLUX_SILICONFLOW_API_KEY=sk-from-dotenv\n")
    monkeypatch.setenv("ANIMAFLUX_DOTENV", str(tmp_path / ".env"))
    monkeypatch.delenv("ANIMAFLUX_SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

    provider = SiliconFlowProvider.from_env()
    assert provider.api_key == "sk-from-dotenv"
