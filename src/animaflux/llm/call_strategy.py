"""LLM Call Strategy（v5.9 §15D）。

LLM 是 Cognitive Capability，不是 Agent 本体（§15D）。Runtime 统一拥有 LLM 调用：Cognitive
Process 不直接调厂商 SDK，而经 LLMCapability → Provider（§15D.1）。每次调用通过受控
LLMCallRequest。技术重试（Technical Retry）复用已成功的非确定结果，避免「数据库失败导致
Agent 重新想一次」（§15D.22）。Retry = technical failure；Repair = 格式违约；Fallback =
切换更保守策略（§15D.23）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from animaflux.kernel.ids import IdGenerator


@dataclass(frozen=True)
class LLMCallRequest:
    """受控 LLM 调用请求（§15D.1）。logical_call_id 跨技术重试保持稳定（§15D.22）。"""

    logical_call_id: str
    process_id: str
    prompt_template_id: str
    prompt_version: str
    input: Any
    branch_id: str = "main"
    tick_id: str | None = None


@dataclass(frozen=True)
class LLMCallRecord:
    """一次已成功 LLM 调用的记录（§15D.20）。validated_structured_result 为已验证输出。"""

    llm_call_id: str
    logical_call_id: str
    provider: str
    model: str
    prompt_template_id: str
    prompt_version: str
    result: Any
    status: str = "SUCCEEDED"
    attempts: int = 1
    retry_lineage: tuple[str, ...] = ()


class LLMProvider(Protocol):
    """配置的 LLM Provider（§15D.1）。"""

    name: str

    def generate(self, request_input: Any) -> Any: ...


class LLMCallStrategy:
    """Runtime-owned LLM 调用 + 技术重试复用（§15D.22）。"""

    def __init__(self, provider: LLMProvider, *, model: str = "default") -> None:
        self._provider = provider
        self._model = model
        self._records: dict[str, LLMCallRecord] = {}
        self._ids = IdGenerator("LLM", width=None)
        self.provider_calls = 0

    def call(self, request: LLMCallRequest) -> LLMCallRecord:
        # §15D.22：技术重试复用已成功的非确定结果，不重复调用 Provider
        existing = self._records.get(request.logical_call_id)
        if existing is not None and existing.status == "SUCCEEDED":
            return existing
        self.provider_calls += 1
        result = self._provider.generate(request.input)
        record = LLMCallRecord(
            llm_call_id=self._ids.next(),
            logical_call_id=request.logical_call_id,
            provider=self._provider.name,
            model=self._model,
            prompt_template_id=request.prompt_template_id,
            prompt_version=request.prompt_version,
            result=result,
        )
        self._records[request.logical_call_id] = record
        return record

    def record_for(self, logical_call_id: str) -> LLMCallRecord | None:
        return self._records.get(logical_call_id)
