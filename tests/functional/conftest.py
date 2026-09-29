"""tests/functional 共享 fixture（只走公开契约，不触碰 Runtime 内部）。

Functional 套件约束（用户约定）：
- 只经公开 API（AnimaFlux / LifeHandle / LifeBranchHandle），不 import StateStore / Resolver /
  TransactionCoordinator / PluginManager 等内部。
- scripted-fake LLM 用确定性替身，验证「LLM 只是 Cognitive Capability，不是 Runtime 主控」（§15D）。
"""

from __future__ import annotations

import pytest

from animaflux.contracts.influence import Influence
from animaflux.kernel.ids import IdGenerator
from animaflux.llm.call_strategy import LLMCallStrategy
from animaflux.llm.providers import LLMProviderError


class _ScriptedProvider:
    """确定性 fake LLM：只做 language realization，不做决策（§15D.3）。"""

    name = "scripted"

    def __init__(self, text: str = "scripted-utterance", *, fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls = 0

    def generate(self, request_input):
        self.calls += 1
        if self.fail:
            raise LLMProviderError("scripted failure")
        return {"text": self.text}


@pytest.fixture
def make_influence():
    """构造跨模块 Influence（与官方 demo.py 的 _influence 同构，§16E）。"""
    ids = IdGenerator("FUNC", width=None)

    def _make(target_state, influence_type, magnitude=0.0, *, created_at, metadata=None) -> Influence:
        return Influence(
            influence_id=ids.next(),
            source_plugin="functional_test",
            target_state=target_state,
            influence_type=influence_type,
            magnitude=magnitude,
            created_at=created_at,
            metadata=metadata or {},
        )

    return _make


@pytest.fixture
def scripted_llm():
    """返回 (LLMCallStrategy, ScriptedProvider)，供 scripted-fake LLM 场景使用（§15D.1）。"""

    def _make(text: str = "scripted-utterance", *, fail: bool = False):
        provider = _ScriptedProvider(text, fail=fail)
        return LLMCallStrategy(provider, model="scripted"), provider

    return _make
