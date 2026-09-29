"""① 生命切片与情绪（§16C / §13B / §13D）。

Scenario 组：初生 → 惊魂一日 → 身体的流逝。只走公开 API（AnimaFlux / LifeHandle）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.state import StateNamespace


def test_birth_seeds_states_and_neutral_emotion():
    """初生：Core State 全部就位，情绪中性，无记忆/信念/关系/目标。"""
    flux = AnimaFlux()
    handle = flux.create_life(
        "func-birth",
        bootstrap=CharacterBootstrap(primary_name="小林", values=("growth", "care")),
    )

    # 12 个 Core State seed；MEMORY 是 Specialized Store，不进 StateStore（§13F.9）
    overview = {row["namespace"]: row for row in handle.state_overview()}
    for ns in StateNamespace:
        expected = ns is not StateNamespace.MEMORY
        assert overview[ns.value]["seeded"] is expected, ns

    identity = handle.inspect(StateNamespace.IDENTITY).data
    assert identity.primary_name == "小林"
    value = handle.inspect(StateNamespace.VALUE).data
    assert {v.value_type for v in value.commitments} == {"growth", "care"}

    emotion = handle.inspect(StateNamespace.EMOTION).data
    assert emotion.episodes == ()
    assert emotion.mood.valence == 0.0
    assert emotion.mood.arousal == 0.0

    # 尚未经历任何事
    assert handle.memories() == ()
    assert handle.inspect(StateNamespace.BELIEF).data.records == ()
    assert handle.inspect(StateNamespace.RELATIONSHIP).data.relationships == ()
    assert handle.inspect(StateNamespace.GOAL).data.goals == ()

    # 生命概览可读且中性
    s = handle.summary()
    assert s.primary_name == "小林"
    assert s.vital_status == "ALIVE"
    assert s.homeostasis.energy == 1.0


def test_threat_day_fear_then_decay():
    """惊魂一日：威胁 → fear（负 valence）→ 时间流逝情绪衰减（§13D.11）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-threat")
    result = handle.send_text("I sense danger ahead.")

    assert result.committed and result.text
    emotion = handle.inspect(StateNamespace.EMOTION).data
    fear = next(e for e in emotion.episodes if e.emotion_type == "fear")
    assert fear.status == "active"
    assert fear.intensity > 0
    assert fear.valence < 0
    assert fear.arousal > 0
    # mood 被负性情绪拉低
    assert emotion.mood.valence < 0

    # 一个情绪半衰期（600s）后：同一 episode 强度衰减、但仍在（Forgetting ≠ 情绪删除）
    handle.advance(600.0)
    emotion2 = handle.inspect(StateNamespace.EMOTION).data
    fear2 = next(e for e in emotion2.episodes if e.emotion_type == "fear")
    assert fear2.intensity < fear.intensity
    assert fear2.status == "active"


def test_body_flows_over_time():
    """身体的流逝：advance 大段时间 → energy 下降、fatigue 累积（§13B.12）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-body")
    body0 = handle.inspect(StateNamespace.BODY).data
    assert body0.homeostasis.energy == 1.0
    assert body0.sleep.fatigue == 0.0

    handle.advance(3600.0)  # 1 小时

    body1 = handle.inspect(StateNamespace.BODY).data
    assert body1.homeostasis.energy < body0.homeostasis.energy
    assert body1.sleep.fatigue > body0.sleep.fatigue
    s = handle.summary()
    assert s.homeostasis.energy < 1.0
