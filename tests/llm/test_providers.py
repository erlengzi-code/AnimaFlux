"""SiliconFlowProvider 与 Runtime LLM 接线测试（§15C.11 / §15D）。

不访问真实网络：Provider 的 HTTP 层用 monkeypatch 打桩；Runtime 接线用 scripted fake
provider。真实网络调用只出现在 `test_live_siliconflow`（默认 skip，需环境变量 opt-in）。
"""

import json
import urllib.error
import urllib.request

import pytest

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace
from animaflux.llm.call_strategy import LLMCallStrategy
from animaflux.llm.providers import LLMProviderError, SiliconFlowProvider


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture_request(monkeypatch, response_payload):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["req"] = req
        return _FakeResponse(response_payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def test_provider_builds_request_and_parses_response(monkeypatch):
    captured = _capture_request(
        monkeypatch,
        {"model": "Qwen/Qwen2.5-7B-Instruct", "choices": [{"message": {"content": "hello there"}}],
         "usage": {"total_tokens": 3}},
    )
    provider = SiliconFlowProvider(api_key="sk-test", model="Qwen/Qwen2.5-7B-Instruct")

    result = provider.generate({"messages": [{"role": "user", "content": "hi"}]})

    assert result["text"] == "hello there"
    # 请求体：OpenAI-compatible /chat/completions
    sent = json.loads(captured["req"].data.decode("utf-8"))
    assert sent["model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sent["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["req"].full_url == "https://api.siliconflow.cn/v1/chat/completions"
    assert captured["req"].get_header("Authorization") == "Bearer sk-test"


def test_provider_http_error_raises_explicit_error(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = SiliconFlowProvider(api_key="sk-bad")

    with pytest.raises(LLMProviderError):
        provider.generate({"messages": [{"role": "user", "content": "hi"}]})


def _neutralize_dotenv(monkeypatch, tmp_path):
    """让 load_dotenv 找不到 .env，避免读到项目根目录的真实 .env（测试确定性）。"""
    monkeypatch.setenv("ANIMAFLUX_DOTENV", str(tmp_path / "no-such-dotenv"))


def test_provider_missing_key_raises_on_generate(monkeypatch, tmp_path):
    _neutralize_dotenv(monkeypatch, tmp_path)
    monkeypatch.delenv("ANIMAFLUX_SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    provider = SiliconFlowProvider()
    with pytest.raises(LLMProviderError):
        provider.generate({"messages": [{"role": "user", "content": "hi"}]})


def test_provider_from_env_raises_when_key_unset(monkeypatch, tmp_path):
    _neutralize_dotenv(monkeypatch, tmp_path)
    monkeypatch.delenv("ANIMAFLUX_SILICONFLOW_API_KEY", raising=False)
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(LLMProviderError):
        SiliconFlowProvider.from_env()


def test_provider_rejects_non_messages_input():
    provider = SiliconFlowProvider(api_key="sk-test")
    with pytest.raises(LLMProviderError):
        provider.generate({"not": "messages"})


# ---------------------------------------------------------------------------
# Runtime 接线：LLM 作为可选 capability，确定性 fallback 不破坏
# ---------------------------------------------------------------------------
class _ScriptedProvider:
    name = "scripted"

    def __init__(self, text="scripted-utterance", fail=False):
        self.text = text
        self.fail = fail
        self.calls = 0

    def generate(self, request_input):
        self.calls += 1
        if self.fail:
            raise LLMProviderError("boom")
        return {"text": self.text}


def test_send_text_uses_llm_when_configured():
    provider = _ScriptedProvider("I think there may be some danger.")
    flux = AnimaFlux(llm=LLMCallStrategy(provider, model="scripted"))
    handle = flux.create_life("llm-life")

    result = handle.send_text("I sense danger ahead.")

    assert provider.calls == 1
    assert result.text == "I think there may be some danger."
    assert result.committed


def test_send_text_falls_back_when_provider_fails():
    provider = _ScriptedProvider(fail=True)
    flux = AnimaFlux(llm=LLMCallStrategy(provider, model="scripted"))
    handle = flux.create_life("llm-fallback")

    result = handle.send_text("I sense danger ahead.")

    # Provider 抛错 → 确定性模板 fallback（§15D.23），Tick 仍 committed
    assert result.text == "Please be careful: there may be danger ahead."
    assert result.committed


def test_no_llm_default_stays_deterministic():
    flux = AnimaFlux()
    handle = flux.create_life("no-llm-default")
    result = handle.send_text("I sense danger ahead.")
    assert result.text == "Please be careful: there may be danger ahead."


@pytest.mark.skipif(
    not __import__("os").environ.get("ANIMAFLUX_SILICONFLOW_API_KEY"),
    reason="设置 ANIMAFLUX_SILICONFLOW_API_KEY 后跑真实网络 smoke test",
)
def test_live_siliconflow_smoke():
    flux = AnimaFlux.from_config({"llm": {"provider": "siliconflow"}})
    handle = flux.create_life("live-smoke")
    result = handle.send_text("I sense danger ahead.")
    assert result.committed
    assert result.text  # 非空自然语言表达
