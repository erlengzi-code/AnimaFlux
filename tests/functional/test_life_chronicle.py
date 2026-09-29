"""⑧ 完整一生（LifeChronicleScenario，§12E §21-24）：出生 → 死亡（自然 / 可预防早死）。

只走公开 API（AnimaFlux / LifeHandle）+ LifeChronicleScenario；Environment 绝不直接写 Core State
（§12E §11），死亡是世界事实，其情绪/信念/叙事意义由生命自身形成。不调 LLM（Deterministic First）。

核心因果地图（§12E §14/§24，Satisficing 专业化 → 不同动机 → 不同死法）：
- growth（只准备）→ 知识不足 → 45 岁病逝（illness）
- competence（只求教）→ 挺过 45，关系不足 → 65 岁意外（accident）
- safety（只联系）→ 知识不足 → 45 岁病逝（illness）
"""

from __future__ import annotations

from datetime import datetime

from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.state import StateNamespace
from animaflux.environment.life_chronicle import LifeChronicleScenario, YEAR_SECONDS
from animaflux.runtime.replay import ReplayEngine

BIRTH = datetime(2000, 1, 1)


def _seed(handle, make_influence, goal_description, need_type):
    """成对播种 goal + need（两者映射同一主动动作，无冲突，§12E）。"""
    return (
        make_influence(StateNamespace.GOAL.value, "goal.propose", 0.6, created_at=handle.now(),
                       metadata={"description": goal_description, "base_importance": 0.6, "urgency": 0.6}),
        make_influence(StateNamespace.DRIVE.value, "drive.need_assess", 0.6, created_at=handle.now(),
                       metadata={"need_type": need_type, "intensity": 0.5, "satisfaction": 0.5}),
    )


def _make_life(life_id, *, primary_name="小林"):
    env = LifeChronicleScenario(birth=BIRTH)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life(life_id, bootstrap=CharacterBootstrap(primary_name=primary_name), start_time=BIRTH)
    return flux, env, handle


def _run_years(env, handle, phase_hook=None):
    """每年 advance + act → 里程碑/危机解析 → 死亡。返回主动行为序列（不含出生播种）。"""
    actions = []
    for age in range(1, 81):
        handle.advance(YEAR_SECONDS)
        if phase_hook:
            phase_hook(handle, age)
        outcome = handle.act()
        actions.append(outcome.intent.action_type if outcome.intent else None)
        batch = env.poll_observations(handle.now())
        if batch.observations:
            handle.step(0.0, observations=batch.observations)
        if not env.state.get("alive", True):
            break
    return actions


def _run(env, handle, seed, phase_hook=None):
    """出生 + 播种动机 → 跑完一生。"""
    handle.step(0.0, observations=(env.birth_observation(),), extra_influences=seed)
    return _run_years(env, handle, phase_hook)


def test_lifetime_growth_dies_of_illness(make_influence):
    """§12E §14：只准备（growth）→ 知识不足 → 45 岁病逝（可预防早死·illness）。"""
    _flux, env, handle = _make_life("life-growth")
    _run(env, handle, _seed(handle, make_influence, "pursue the perceived opportunity", "growth"))

    assert env.state.get("alive") is False
    assert env.state.get("death_cause") == "illness"
    assert env.state.get("age_at_death") == 45


def test_lifetime_competence_dies_of_accident(make_influence):
    """§12E §14：只求教（competence）→ 挺过 illness@45，但关系不足 → 65 岁意外（accident）。"""
    _flux, env, handle = _make_life("life-competence")
    _run(env, handle, _seed(handle, make_influence, "maintain the perceived gain", "competence"))

    assert env.state.get("alive") is False
    assert env.state.get("death_cause") == "accident"
    assert env.state.get("age_at_death") == 65


def test_lifetime_same_birth_different_fates(make_influence):
    """§12E §20：同一出生、同一世界，因主动选择不同 → 不同死法/寿命。"""
    _f1, env_g, h_g = _make_life("fates-growth")
    _run(env_g, h_g, _seed(h_g, make_influence, "pursue the perceived opportunity", "growth"))

    _f2, env_c, h_c = _make_life("fates-competence")
    _run(env_c, h_c, _seed(h_c, make_influence, "maintain the perceived gain", "competence"))

    assert (env_g.state.get("death_cause"), env_g.state.get("age_at_death")) != \
           (env_c.state.get("death_cause"), env_c.state.get("age_at_death"))
    assert env_g.state.get("death_cause") == "illness"
    assert env_c.state.get("death_cause") == "accident"


def test_lifetime_environment_boundary(make_influence):
    """§12E §11/§12：Environment 只改外部世界事实，绝不持有/写 Core State。"""
    flux, env, handle = _make_life("life-boundary")
    seed = _seed(handle, make_influence, "pursue the perceived opportunity", "growth")
    handle.step(0.0, observations=(env.birth_observation(),), extra_influences=seed)
    before = handle.inspect(StateNamespace.GOAL).data.goals[0].status

    _run_years(env, handle)

    # 环境不持有 StateStore / backend；世界事实变了，但 Core State 未被环境直接改动
    assert not hasattr(env, "store")
    assert not hasattr(env, "backend")
    assert env.state.get("death_cause") == "illness"
    assert handle.inspect(StateNamespace.GOAL).data.goals[0].status == before


def test_lifetime_chronicle(make_influence):
    """§12E §25/§26：编年史非空，含出生与死亡，交织世界事件与主动行为。"""
    _flux, env, handle = _make_life("life-chronicle")
    actions = _run(env, handle, _seed(handle, make_influence, "pursue the perceived opportunity", "growth"))

    chronicle = env.chronicle()
    assert chronicle
    assert any("出生" in line for line in chronicle)
    assert any("早死" in line for line in chronicle)
    assert actions  # 生命生前确实主动行动过


def test_lifetime_replay_exactness(make_influence):
    """§12E §20 / §21.3：完整一生可只读回放，llm_calls=0 / write_ops=0。"""
    flux, env, handle = _make_life("life-replay")
    _run(env, handle, _seed(handle, make_influence, "pursue the perceived opportunity", "growth"))

    engine = ReplayEngine(flux.backend)
    ticks = engine.replay_timeline("life-replay")

    assert engine.llm_calls == 0
    assert engine.write_ops == 0
    assert len(ticks) > 0


def test_lifetime_natural_death(make_influence):
    """§12E §21-24：动机随人生阶段切换（先求教后联系）→ 挺过两次危机 → 80 岁自然死亡。"""
    flux, env, handle = _make_life("life-balanced")

    # phase1：gain goal（seek_feedback）攒知识挺过 illness@45；phase2：完成所有旧目标（含里程碑注入的
    # loss/opportunity 目标）并换 threat goal（communicate）攒关系挺过 accident@65。
    gain_goal = make_influence(StateNamespace.GOAL.value, "goal.propose", 0.6, created_at=handle.now(),
                               metadata={"description": "maintain the perceived gain", "base_importance": 0.6, "urgency": 0.6})

    def _phase_hook(h, age):
        if age != 46:
            return
        goals = h.inspect(StateNamespace.GOAL).data.goals
        completes = tuple(
            make_influence(StateNamespace.GOAL.value, "goal.complete", 0.0, created_at=h.now(),
                           metadata={"goal_id": g.goal_id})
            for g in goals if g.status in ("PROPOSED", "ACTIVE", "PAUSED")
        )
        threat = make_influence(StateNamespace.GOAL.value, "goal.propose", 0.6, created_at=h.now(),
                                metadata={"description": "avoid the perceived threat", "base_importance": 0.6, "urgency": 0.6})
        h.step(0.0, extra_influences=completes + (threat,))

    _run(env, handle, (gain_goal,), phase_hook=_phase_hook)

    assert env.state.get("alive") is False
    assert env.state.get("death_cause") == "natural"
    assert env.state.get("age_at_death") == 80
