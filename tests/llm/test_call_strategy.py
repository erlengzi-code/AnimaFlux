"""LLM Call Strategy 测试（§15D.22 技术重试复用 / §15D.20 记录）。"""

from animaflux.llm.call_strategy import LLMCallRequest, LLMCallStrategy


class _CountingProvider:
    name = "fake-provider"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request_input):
        self.calls += 1
        return {"text": f"thought-{self.calls}"}


def _request(logical_call_id: str = "LOGIC-1") -> LLMCallRequest:
    return LLMCallRequest(
        logical_call_id=logical_call_id,
        process_id="decision",
        prompt_template_id="tpl-1",
        prompt_version="v1",
        input={"goal": "present"},
    )


def test_technical_retry_reuses_record():
    provider = _CountingProvider()
    strategy = LLMCallStrategy(provider, model="test")

    first = strategy.call(_request())
    second = strategy.call(_request())  # 技术重试：同一 logical_call_id

    assert first.result == second.result
    assert first.logical_call_id == second.logical_call_id
    assert first.status == "SUCCEEDED"
    # 非确定结果被复用，provider 只调用一次（§15D.22）
    assert provider.calls == 1
    assert strategy.provider_calls == 1


def test_distinct_logical_calls_do_not_reuse():
    provider = _CountingProvider()
    strategy = LLMCallStrategy(provider, model="test")

    a = strategy.call(_request("LOGIC-A"))
    b = strategy.call(_request("LOGIC-B"))

    assert a.logical_call_id != b.logical_call_id
    assert provider.calls == 2


def test_record_for_lookup():
    provider = _CountingProvider()
    strategy = LLMCallStrategy(provider, model="test")

    rec = strategy.call(_request("LOGIC-7"))
    assert strategy.record_for("LOGIC-7") is rec
    assert strategy.record_for("LOGIC-missing") is None
