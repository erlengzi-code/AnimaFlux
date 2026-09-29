"""P8 Decision Process 测试（§14D：四阶段 / Satisficing / 硬约束 / NO_ACTION）。"""

from animaflux.plugins.default_cognition.decision import DecisionProcess, make_candidate


def test_four_stages_in_trace():
    p = DecisionProcess()
    frame = p.frame("decide what to do")
    result = p.decide(frame, [make_candidate("a1", "wait", feasibility=0.9)])
    assert result.trace["stages"] == ("framing", "generation", "evaluation", "selection")
    assert result.frame_ref == frame.frame_id


def test_satisficing_picks_first_acceptable():
    p = DecisionProcess()
    frame = p.frame("x")
    result = p.decide(frame, [
        make_candidate("a1", "wait", feasibility=0.8),
        make_candidate("a2", "act", feasibility=0.9),
    ])
    assert result.selected_candidate_ref == "a1"  # 找到第一个可接受即停（§14D.11）
    assert result.rejected_candidate_refs == ("a2",)


def test_hard_violation_candidate_rejected():
    p = DecisionProcess()
    frame = p.frame("x")
    result = p.decide(frame, [
        make_candidate("bad", "act", feasibility=0.0),  # 不可行 = 硬约束（§14D.12）
        make_candidate("good", "wait", feasibility=0.8),
    ])
    assert result.selected_candidate_ref == "good"
    assert "bad" in result.rejected_candidate_refs


def test_no_action_when_all_infeasible():
    p = DecisionProcess()
    frame = p.frame("x")
    result = p.decide(frame, [make_candidate("a", "act", feasibility=0.1)])
    assert result.selected_candidate_ref is None
    assert result.no_action_reason is not None  # NO_ACTION 是合法决策（§14D.2）


def test_candidate_budget_limits_generation():
    p = DecisionProcess(candidate_budget=2)
    frame = p.frame("x")
    result = p.decide(frame, [make_candidate(f"a{i}", "wait", feasibility=0.9) for i in range(5)])
    assert result.trace["evaluated"] == 2  # Candidate Generation 受 budget 限制（§14D.6）
