"""⑦ 主观能动性与主动行为（§12E / §27.1–27.5）：Life ↔ World 双向循环。

只走公开 API（AnimaFlux / LifeHandle）+ ScenarioEnvironment；Environment 绝不直接写 Core State
（§12E §11），Action 结果只经 Observation 回灌。不调 LLM（Deterministic First）。
"""

from __future__ import annotations

from datetime import datetime

from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.state import StateNamespace
from animaflux.environment.scenario import FirstPresentationScenario


def _seed_opportunity(handle, make_influence):
    """播种「机会」目标 + growth 需要（与 motivation 的 opportunity→growth 同构）。"""
    return (
        make_influence(
            StateNamespace.GOAL.value, "goal.propose", 0.6,
            created_at=handle.now(),
            metadata={"description": "pursue the perceived opportunity",
                      "base_importance": 0.6, "urgency": 0.6},
        ),
        make_influence(
            StateNamespace.DRIVE.value, "drive.need_assess", 0.6,
            created_at=handle.now(),
            metadata={"need_type": "growth", "intensity": 0.5, "satisfaction": 0.5},
        ),
    )


def test_proactive_agency_without_external_trigger(make_influence):
    """§27.1 无外部触发仍主动行动：只有内部动机（goal+need）也产出 ActionIntent。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 8), required_preparation=2)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("agency-1", bootstrap=CharacterBootstrap(values=("growth",)))
    handle.step(1.0, extra_influences=_seed_opportunity(handle, make_influence))

    outcome = handle.act()

    assert outcome.acted is True
    assert outcome.intent is not None
    assert outcome.intent.action_type == "prepare_task"
    assert outcome.intent.initiative == "proactive"
    assert env.state.get("preparation", 0) == 1


def test_environment_boundary_never_writes_core_state(make_influence):
    """§27.2 环境边界：ScenarioEnvironment 只改世界事实，绝不直接写 Core State。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 8), required_preparation=2)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("agency-2", bootstrap=CharacterBootstrap(values=("growth",)))
    handle.step(1.0, extra_influences=_seed_opportunity(handle, make_influence))
    before = handle.inspect(StateNamespace.GOAL).data.goals[0].status

    handle.act()

    # 环境不持有 StateStore / backend，只能经 Observation 回灌
    assert not hasattr(env, "store")
    assert not hasattr(env, "backend")
    # 世界事实变了（外部），但生命 Core State 未被环境直接改动
    assert env.state.get("preparation", 0) == 1
    assert handle.inspect(StateNamespace.GOAL).data.goals[0].status == before


def test_agency_consequence_changes_world_and_life(make_influence):
    """§27.3 行动后果：prepare 改变世界，演讲日按准备度裁决，成功 → joy。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 3), required_preparation=1)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life(
        "agency-3", bootstrap=CharacterBootstrap(values=("growth",)), start_time=datetime(2000, 1, 1)
    )
    handle.step(1.0, extra_influences=_seed_opportunity(handle, make_influence))

    handle.act()  # prepare → preparation=1

    handle.advance(172800.0)  # +2 天，到演讲日
    batch = env.poll_observations(handle.now())
    handle.step(0.0, observations=batch.observations)

    assert env.state.get("presentation_success") is True
    emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    assert "joy" in emotions


def test_underprepared_failure_yields_loss(make_influence):
    """§27.3（失败分支）：准备不足 → 演讲失败 → loss（sadness）。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 3), required_preparation=5)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life(
        "agency-3b", bootstrap=CharacterBootstrap(values=("growth",)), start_time=datetime(2000, 1, 1)
    )
    handle.step(1.0, extra_influences=_seed_opportunity(handle, make_influence))

    handle.act()  # 只准备一次，preparation=1 < 5

    handle.advance(172800.0)
    batch = env.poll_observations(handle.now())
    handle.step(0.0, observations=batch.observations)

    assert env.state.get("presentation_success") is False
    emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    assert "sadness" in emotions


def test_knowledge_seeking_agency():
    """§27.4 求知主动：信息缺口（空 World Model）→ seek_feedback。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 8), required_preparation=2)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("agency-4", bootstrap=CharacterBootstrap(values=("growth",)))

    outcome = handle.act()

    assert outcome.acted is True
    assert outcome.intent is not None
    assert outcome.intent.action_type == "seek_feedback"


def test_replay_does_not_refire_agency(make_influence):
    """§27.5 Replay 兼容：timeline 只读，不重放主动决策、不再触发环境。"""
    env = FirstPresentationScenario(presentation_at=datetime(2000, 1, 8), required_preparation=2)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("agency-5", bootstrap=CharacterBootstrap(values=("growth",)))
    handle.step(1.0, extra_influences=_seed_opportunity(handle, make_influence))
    handle.act()
    assert env.resolve_count == 1
    goal_version = handle.inspect(StateNamespace.GOAL).version

    handle.timeline()
    handle.timeline()

    assert env.resolve_count == 1
    assert handle.inspect(StateNamespace.GOAL).version == goal_version
