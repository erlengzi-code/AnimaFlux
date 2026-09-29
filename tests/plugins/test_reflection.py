"""P9 Reflection Process 测试（§14F：只产出 Proposal/Evidence，不直接改 State）。"""

from animaflux.contracts.reflection import ReflectionResult
from animaflux.plugins.default_cognition.reflection import EvidenceItem, ReflectionProcess


def test_reflection_is_proposal_only():
    # Reflection 是 Process，不是 Owner：没有 resolve，不能写任何 State（§14F.4）
    proc = ReflectionProcess()
    assert not hasattr(proc, "resolve")
    result = proc.reflect("scope-1", [
        EvidenceItem("EV-1", "goal_failure", "ask_raise", "raise request denied"),
        EvidenceItem("EV-2", "goal_failure", "ask_raise", "raise request denied again"),
    ])
    assert isinstance(result, ReflectionResult)
    assert not hasattr(result, "next_state")  # 不产出 State（§14F.4）
    assert result.goal_review_evidence  # 只产出 Evidence 供 Goal Owner 决定


def test_insufficient_evidence_is_valid():
    # 证据不足是合法结果，不是错误（§14F.12）
    proc = ReflectionProcess()
    result = proc.reflect("scope-1", [])
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.pattern_candidates == ()


def test_single_observation_is_tentative():
    proc = ReflectionProcess()
    result = proc.reflect("scope-1", [EvidenceItem("EV-1", "self", "confidence", "felt good")])
    assert result.status == "TENTATIVE"


def test_repeated_pattern_produces_candidate():
    proc = ReflectionProcess()
    result = proc.reflect("scope-1", [
        EvidenceItem("EV-1", "goal_failure", "ask_raise", "denied"),
        EvidenceItem("EV-2", "goal_failure", "ask_raise", "denied again"),
    ])
    assert len(result.pattern_candidates) == 1
    p = result.pattern_candidates[0]
    assert p.kind == "goal_failure"
    assert p.occurrence_count == 2
    assert p.evidence_refs == ("EV-1", "EV-2")
    assert result.status == "SUPPORTED"


def test_proposals_carry_source_refs():
    # Proposal / Evidence 都挂 source_refs，供 Owner 决定是否采纳（§14F.4）
    proc = ReflectionProcess()
    result = proc.reflect("scope-1", [
        EvidenceItem("EV-1", "goal_failure", "ask_raise", "denied"),
        EvidenceItem("EV-2", "goal_failure", "ask_raise", "denied again"),
    ])
    assert result.source_refs == ("EV-1", "EV-2")
    assert result.belief_revision_proposals  # 失败模式触发 belief 重估 proposal
