"""④ 慢自我发展（§13C/§13H/§13L/§13M + §14F）。

Scenario：复盘人生（反复威胁 → Narrative/Personality/Self）→ 显式反思 → 反复失去 → Value。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace


def test_repeated_threat_reflects_slow_development():
    """复盘人生：反复威胁 → 反思沉淀 Narrative / Personality / Self Model（§14F.9/§14F.10）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-reflect")
    for _ in range(3):
        handle.observe_text("there is danger nearby")

    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    themes = [t for t in narrative.themes if t.name == "safety vigilance"]
    assert themes
    assert themes[0].source_refs  # provenance（§13M.3/§13M.12）

    personality = handle.inspect(StateNamespace.PERSONALITY).data
    trait = next(t for t in personality.traits if t.name == "emotional_reactivity")
    assert 0.5 < trait.value < 0.6  # bounded 微升（§13C.13）

    self_model = handle.inspect(StateNamespace.SELF_MODEL).data
    assert 0.3 <= self_model.self_esteem < 0.5  # bounded 微降（§13L.15）


def test_insufficient_evidence_keeps_slow_state():
    """证据不足不反思，慢状态不变（§14F.12 低频）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-quiet")
    handle.observe_text("there is danger nearby")  # 仅 1 条

    assert handle.inspect(StateNamespace.NARRATIVE).data.themes == ()
    personality = handle.inspect(StateNamespace.PERSONALITY).data
    assert all(t.value == 0.5 for t in personality.traits)
    assert handle.inspect(StateNamespace.SELF_MODEL).data.self_esteem == 0.5


def test_reflect_now_forces_slow_update():
    """显式触发反思（§14F.1）在阈值以下也能沉淀。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-force")
    handle.observe_text("there is danger nearby")
    handle.observe_text("there is danger nearby")  # 2 条 < 自动阈值 3

    handle.reflect_now()

    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    assert any(t.name == "safety vigilance" for t in narrative.themes)


def test_repeated_loss_forms_value_commitment():
    """反复失去 → 反思形成/强化 Value（§13H.11 默认领域 stability）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-value")
    for _ in range(3):
        handle.observe_text("we suffered a great loss")

    value = handle.inspect(StateNamespace.VALUE).data
    assert any(v.value_type == "stability" for v in value.commitments)
