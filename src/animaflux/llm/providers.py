"""Concrete LLM Providers（v5.9 §15C.11 / §15D.1）。

Provider 只是 Cognitive Capability 的实现（§15D.1）：Cognitive Process 不直接调厂商 SDK，
统一经 LLMCapability → Configured LLM Provider。这里提供 OpenAI-compatible 的远程 Provider
（硅基流动 SiliconFlow）。实现只依赖标准库 urllib，不引入第三方 HTTP 依赖。

Secret 处理：API Key 一律不硬编码，从环境变量读取（ANIMAFLUX_SILICONFLOW_API_KEY，回退
SILICONFLOW_API_KEY），也可显式传参。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from animaflux.config.env import load_dotenv
from animaflux.llm.call_strategy import LLMProvider

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

_ENV_KEYS = ("ANIMAFLUX_SILICONFLOW_API_KEY", "SILICONFLOW_API_KEY")


class LLMProviderError(RuntimeError):
    """Provider 调用失败（网络 / 鉴权 / 空响应）。上层据此走确定性 fallback（§15D.23）。"""


class SiliconFlowProvider:
    """OpenAI-compatible 远程 Provider（硅基流动）。§15C.11「OpenAI-compatible」。"""

    name = "siliconflow"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or _env_api_key()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls, *, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL) -> "SiliconFlowProvider":
        """从环境变量构造；未配置 key 时抛出明确错误（避免静默空 key）。"""
        key = _env_api_key()
        if not key:
            raise LLMProviderError(
                "SiliconFlow API key 未配置：请设置 ANIMAFLUX_SILICONFLOW_API_KEY 环境变量。"
            )
        return cls(api_key=key, model=model, base_url=base_url)

    def generate(self, request_input: Any) -> dict:
        """调用 /chat/completions（OpenAI 兼容）。request_input 形如
        `{"messages": [{"role", "content"}], "max_tokens": ..., "temperature": ...}`。"""
        if not self.api_key:
            raise LLMProviderError("SiliconFlow API key 未配置。")

        if not isinstance(request_input, dict) or "messages" not in request_input:
            raise LLMProviderError("LLM 输入必须是含 `messages` 的 dict。")

        payload = {
            "model": self.model,
            "messages": request_input["messages"],
            "max_tokens": request_input.get("max_tokens", 256),
            "temperature": request_input.get("temperature", 0.7),
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMProviderError(f"SiliconFlow HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMProviderError(f"SiliconFlow 网络错误: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(f"SiliconFlow 响应缺少 choices[0].message.content: {body}") from exc

        return {
            "text": content,
            "model": body.get("model", self.model),
            "usage": body.get("usage", {}),
        }


def _env_api_key() -> str | None:
    # 先加载 .env（若尚未在环境变量里），再读环境变量（§15C.11 密钥不硬编码进源码）。
    load_dotenv()
    for name in _ENV_KEYS:
        value = os.environ.get(name)
        if value:
            return value
    return None


__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "SiliconFlowProvider",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
]
