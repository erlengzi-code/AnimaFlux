"""⑥ scripted-fake LLM 场景（§15D）：LLM 只是 Cognitive Capability，不是 Runtime 主控。

用确定性 fake provider 验证：语言实现交给 LLM，但状态决议（情绪/动机落地）仍由代码保证；
LLM 失败回退确定性模板，不阻塞生命 Tick（§15D.23）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace


def test_scripted_llm_realizes_utterance_and_state_still_lands(scripted_llm):
    """配置 scripted-fake LLM：回应用 scripted 文本，但 fear 情绪照常落地（§15D.3）。"""
    llm, provider = scripted_llm("I think there may be some danger.")
    flux = AnimaFlux(llm=llm)
    handle = flux.create_life("func-llm")

    result = handle.send_text("I sense danger ahead.")

    assert provider.calls == 1
    assert result.text == "I think there may be some danger."
    assert result.committed
    # LLM 只做语言实现，不影响确定性状态决议
    emotion = handle.inspect(StateNamespace.EMOTION).data
    assert any(e.emotion_type == "fear" for e in emotion.episodes)


def test_scripted_llm_failure_falls_back_deterministic(scripted_llm):
    """LLM 失败 → 确定性模板 fallback，Tick 仍 committed（§15D.23）。"""
    llm, _ = scripted_llm(fail=True)
    flux = AnimaFlux(llm=llm)
    handle = flux.create_life("func-llm-fallback")

    result = handle.send_text("I sense danger ahead.")

    assert result.text == "Please be careful: there may be danger ahead."
    assert result.committed


def test_no_llm_default_stays_deterministic():
    """不配置 LLM：全确定性，同输入同输出（Deterministic First，§15D.2）。"""
    flux = AnimaFlux()
    h1 = flux.create_life("func-no-llm-1")
    h2 = flux.create_life("func-no-llm-2")
    r1 = h1.send_text("I sense danger ahead.")
    r2 = h2.send_text("I sense danger ahead.")
    assert r1.text == r2.text == "Please be careful: there may be danger ahead."
