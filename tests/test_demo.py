"""官方 Demo（§16E）端到端冒烟测试。"""

from animaflux.demo import run_demo_a, run_demo_b


def test_demo_a_experience_growth():
    a = run_demo_a()
    # 生命在 Day 1–6 无外部触发下主动准备（§12E）
    assert a["agency_actions"]
    assert "prepare_task" in a["agency_actions"]
    # 准备充分 → 演讲成功 → 阅历增长落到 public_speaking 自我效能
    assert a["presentation_success"] is True
    assert a["final_preparation"] >= 2
    assert "public_speaking" in a["self_efficacy_domains"]
    # 成功 → joy
    assert "joy" in a["emotion_types"]
    # 可保存 + 可重放
    assert a["checkpoint_id"]
    assert a["replay_tick_count"] > 0


def test_demo_b_relationship_branch():
    b = run_demo_b()
    # 两个分支 id 不同
    assert b["branch_a_id"] != b["branch_b_id"]
    # post-fork 分叉
    assert b["diverged"] is True
    # pre-fork 历史共享（trust 未在分支中改变）
    assert b["shared_prefork_trust"] is True
