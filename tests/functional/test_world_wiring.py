"""⑧ 世界接入（§12E）：Public Facade 的场景工厂 + advance_world / world_view。

验证 per-life world 装配、advance 自动 poll 排程事件（单 Tick，修「空推进」）、只读世界事实视图。
只走公开 API（AnimaFlux / LifeHandle / build_scenario_environment），不 import 环境内部实现细节
（Functional 套件约束，见 conftest.py）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux, CharacterBootstrap, build_scenario_environment
from animaflux.environment.life_chronicle import LifeChronicleScenario
from animaflux.environment.scenario import FirstPresentationScenario


def test_build_scenario_environment_returns_correct_types():
    env, stype = build_scenario_environment("presentation")
    assert isinstance(env, FirstPresentationScenario)
    assert stype == "presentation"

    env, stype = build_scenario_environment("chronicle")
    assert isinstance(env, LifeChronicleScenario)
    assert stype == "chronicle"

    assert build_scenario_environment("none") == (None, None)
    assert build_scenario_environment("") == (None, None)
    assert build_scenario_environment("bogus") == (None, None)


def test_advance_world_fires_scheduled_event_single_tick():
    env, _ = build_scenario_environment("presentation")
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("world-1", bootstrap=CharacterBootstrap(values=("growth",)))
    before = len(handle.timeline())

    tick_id = handle.advance_world(8 * 86400.0)  # 推进 8 天，跨过演讲日（presentation_at=01-08）

    assert tick_id
    assert env.state.get("presentation_done") is True
    assert env.state.get("presentation_success") is False
    # 推进 + 排程事件回灌在同一次 step 内完成：时间线只多 1 条（无「空推进」Tick）
    assert len(handle.timeline()) == before + 1


def test_world_view_chronicle():
    env, _ = build_scenario_environment("chronicle")
    flux = AnimaFlux(environment=env)
    handle = flux.create_life("world-2")
    handle.step(0.0, observations=(env.birth_observation(),))

    view = handle.world_view()
    assert view["facts"]["alive"] is True
    assert "chronicle" in view and "death_info" in view

    handle.advance_world(6 * 365 * 86400.0)  # 到 6 岁 → 入学里程碑
    view = handle.world_view()
    assert any("入学" in line for line in view["chronicle"])


def test_world_view_none_without_environment():
    handle = AnimaFlux().create_life("world-3")
    assert handle.world_view() is None
