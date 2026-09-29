"""P9 Slow Self Development 测试（§13C/§13H/§13L/§13M + §14F）。

验证 Reflection 把长期重复模式沉淀成慢状态 bounded 更新：
反复威胁 → Narrative Theme（Provenance）+ Personality + Self Model；反复失去 → Value。
确定性优先（§15D.2）：全程无 LLM；Reflection 只产出 Proposal/Evidence（§14F.4），
最终由各 Owner 裁决且幅度 bounded + evidence-driven（§14F.9）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace


def test_repeated_threat_reflects_slow_development():
    """反复威胁 → 反思触发 → Narrative/Personality/Self Model 慢更新（§14F.9/§14F.10）。"""
    flux = AnimaFlux()
    handle = flux.create_life("p9-slow")
    for _ in range(3):
        handle.observe_text("there is danger nearby")

    # Narrative：出现 safety theme，带 provenance（§13M.3/§13M.12）
    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    themes = [t for t in narrative.themes if t.name == "safety vigilance"]
    assert themes
    assert themes[0].source_refs

    # Personality：emotional_reactivity 微升，幅度 bounded（§13C.13）
    personality = handle.inspect(StateNamespace.PERSONALITY).data
    trait = next(t for t in personality.traits if t.name == "emotional_reactivity")
    assert trait.value > 0.5
    assert trait.value < 0.6

    # Self Model：esteem 微降，幅度 bounded（§13L.15）
    self_model = handle.inspect(StateNamespace.SELF_MODEL).data
    assert 0.5 > self_model.self_esteem >= 0.3


def test_insufficient_evidence_does_not_change_slow_state():
    """证据不足（未达阈值）不反思，慢状态不变（§14F.12 低频 + §14F.9 bounded）。"""
    flux = AnimaFlux()
    handle = flux.create_life("p9-quiet")
    handle.observe_text("there is danger nearby")  # 仅 1 条，未达阈值

    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    assert narrative.themes == ()
    personality = handle.inspect(StateNamespace.PERSONALITY).data
    assert all(t.value == 0.5 for t in personality.traits)
    self_model = handle.inspect(StateNamespace.SELF_MODEL).data
    assert self_model.self_esteem == 0.5


def test_reflect_now_forces_slow_update():
    """显式触发 Reflection（§14F.1 Trigger）在阈值以下也能沉淀。"""
    flux = AnimaFlux()
    handle = flux.create_life("p9-force")
    handle.observe_text("there is danger nearby")
    handle.observe_text("there is danger nearby")  # 2 条，低于自动阈值 3

    handle.reflect_now()

    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    assert any(t.name == "safety vigilance" for t in narrative.themes)


def test_repeated_loss_forms_value_commitment():
    """反复失去 → 反思形成/强化 Value（§13H.11 默认领域 stability）。"""
    flux = AnimaFlux()
    handle = flux.create_life("p9-value")
    for _ in range(3):
        handle.observe_text("we suffered a great loss")

    value = handle.inspect(StateNamespace.VALUE).data
    assert any(v.value_type == "stability" for v in value.commitments)
