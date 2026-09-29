"""② 认知闭环与知识边界（§14 / §13F / §16B）。

Scenario：完整认知闭环 → 「不知道」≠「不记得」→ 同输入不同时点不同评价（阅历成长）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.state import StateNamespace


def test_full_cognition_loop():
    """threat 消息 → Emotion + Drive + Goal + Relationship + 回应（§15B.10）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-loop")
    result = handle.send_text("I sense danger ahead.")

    assert result.committed and result.text
    emotion = handle.inspect(StateNamespace.EMOTION).data
    assert any(e.emotion_type == "fear" for e in emotion.episodes)
    drive = handle.inspect(StateNamespace.DRIVE).data
    assert any(n.need_type == "safety" for n in drive.needs)
    goal = handle.inspect(StateNamespace.GOAL).data
    assert any(g.description == "avoid the perceived threat" for g in goal.goals)
    # Proposal ≠ Active（§13I.6）：目标只是被提议，未自动激活
    assert all(g.status == "PROPOSED" for g in goal.goals)
    rel = handle.inspect(StateNamespace.RELATIONSHIP).data
    humans = [r for r in rel.relationships if r.target_id == "human"]
    assert humans and humans[0].first_impression is True


def test_knowledge_boundary_never_fabricates():
    """「不知道」：从未感知的事实检索不到，也不编造（§13F.25 / §14C.19）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-boundary")
    assert handle.memories() == ()  # 初生：零记忆

    handle.send_text("I sense danger ahead.")
    assert handle.memories()

    # 已有「danger」记忆，但从未经历「皇帝遇刺」→ 检索结果不含该事实
    unknown = handle.retrieve("皇帝遇刺")
    assert not any("皇帝" in str(m.content) for m in unknown.memories)

    # 而真实经历过的「danger」检索得到
    found = handle.retrieve("danger")
    assert found.status == "FOUND"
    assert any("danger" in str(m.content) for m in found.memories)


def test_stored_not_retrievable_is_not_delete():
    """「不记得」≠「删了」：accessibility 门控下检索不到，但记忆仍在（§14C.5 / §13F.15）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-forget")
    handle.send_text("I sense danger ahead.")

    stored = handle.memories()
    assert stored
    # 提高 min_accessibility 门控 → 当前检索不到（Stored ≠ Retrievable）
    gated = handle.retrieve("danger", min_accessibility=1.01)
    assert not gated.memories
    # 但记忆并未被删除
    assert handle.memories() == stored


def test_same_input_different_time_different_appraisal(make_influence):
    """阅历成长：首次公开演讲恐惧，获得自我效能后同类成功 → 情绪不同（§16E.2–6）。"""
    flux = AnimaFlux()
    handle = flux.create_life(
        "func-experience",
        bootstrap=CharacterBootstrap(primary_name="小林", values=("growth",)),
    )

    first = handle.send_text("I sense danger — tomorrow I must give my first public presentation.")
    first_emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    assert "fear" in first_emotions

    # 演讲成功 → 阅历增长：self-efficacy 的 evidence-driven 更新（§16E.4）
    efficacy = make_influence(
        StateNamespace.SELF_MODEL.value, "self_model.efficacy_update", 0.6,
        created_at=handle.now(),
        metadata={"domain": "public_speaking", "assessment": 0.65, "evidence_refs": ("ev-talk-success-1",)},
    )
    handle.step(1.0, extra_influences=(efficacy,))

    self_model = handle.inspect(StateNamespace.SELF_MODEL).data
    assert any(a.domain == "public_speaking" for a in self_model.self_efficacy)
    # 自我效能是领域特定的，不等于全局自尊（§24 原则 6）
    assert self_model.self_esteem == 0.5

    # 同类情境（成功）：joy —— 同输入不同时点不同评价（§16E.5）
    second = handle.send_text("The presentation was a great success!")
    second_emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    assert "joy" in second_emotions
    assert first.text != second.text
