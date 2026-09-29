"""P8 Motivation & Social Cognition 测试（§13E/§13G/§13I/§13J + §14D Decision）。

验证第一个完整 Human Cognition Loop 的动机与社会认知接线：
Human Message → Perception → Retrieval → Appraisal → Emotion/Drive/Belief/Relationship
→ Goal Review → Decision → CommunicativeIntent → Communication → Human。

确定性优先（§15D.2）：全程无需 LLM；Decision 由代码四阶段完成，LLM 仅 language realization。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.environment import Observation
from animaflux.contracts.state import StateNamespace


def test_send_text_full_cognition_loop():
    """threat 消息 → 完整认知：Emotion(fear) + Drive(safety) + Goal(propose) + Relationship(human) + 回应。"""
    flux = AnimaFlux()
    handle = flux.create_life("p8-loop")
    result = handle.send_text("I sense danger ahead.")
    assert result.committed
    assert result.text  # Decision → Communication 产出确定性回应（§14D → §14E）

    # Emotion：threat → fear 落地（§15B.10）
    emotion = handle.inspect(StateNamespace.EMOTION).data
    assert any(e.emotion_type == "fear" for e in emotion.episodes)

    # Drive：threat → safety Need 评估（§13E.5 Need = 我缺什么）
    drive = handle.inspect(StateNamespace.DRIVE).data
    assert any(n.need_type == "safety" for n in drive.needs)

    # Goal：threat → 提议 goal（§13I.6 Proposal ≠ Active）
    goal = handle.inspect(StateNamespace.GOAL).data
    assert any(g.description == "avoid the perceived threat" for g in goal.goals)
    assert all(g.status == "PROPOSED" for g in goal.goals)

    # Relationship：针对 human 的 directional 关系（§13J.2 / §13J.14 First Impression）
    rel = handle.inspect(StateNamespace.RELATIONSHIP).data
    humans = [r for r in rel.relationships if r.target_id == "human"]
    assert humans
    assert humans[0].first_impression is True


def test_belief_forms_from_observation():
    """显著非 communication 观察 → 形成有证据的 Belief（§13G.11 Evidence-driven）。"""
    flux = AnimaFlux()
    handle = flux.create_life("p8-belief")
    obs = Observation(
        observation_id="o1",
        modality="observation",
        content="danger ahead",
        world_time=handle.now(),
        clarity=1.0,
        intensity=1.0,
        source_entity="human",
    )
    handle.observe(obs)
    belief = handle.inspect(StateNamespace.BELIEF).data
    assert belief.records
    # 无 misperception → 有感知证据支撑，非低置信 Hypothesis（§13G.11 / §13G.44）
    assert all(b.evidence for b in belief.records)


def test_decision_driven_response_prioritizes_threat():
    """Decision 候选按 Appraisal Tag 优先级选择（§14D.43 policy）：threat 优先。"""
    flux = AnimaFlux()
    handle = flux.create_life("p8-decision")
    result = handle.send_text("danger! a threat is near")
    assert result.committed
    # threat → WARN speech_act 的确定性表达（§14E.3 SPEECH_ACT_PREFIX）
    assert "careful" in result.text.lower()
    assert "danger" in result.text.lower()
