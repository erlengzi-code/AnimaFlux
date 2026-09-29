"""官方 Demo（v5.9 §16E / §12E）。

演示一个数字生命「持续存在、会积累经历、会形成关系、会因过去而改变，并且可以被保存、
解释、重放与分支」，以及「世界塑造生命，生命也反过来作用于世界」（§12E）。

- 主线 A（多日 Growing Year，§12E §21-22）：世界排期一场演讲，生命在 Day 1–6 无外部触发下
  主动准备（prepare_task / seek_feedback），Day 7 世界按准备度解析演讲 → 成功（joy）+ 阅历增长
  （self-efficacy）。
- 主线 B（关系转折 + 分支，§16E.10–§16E.16）：与人类用户建立关系 → Checkpoint → Fork 两个
  Branch，展示 post-fork 独立演化、pre-fork 共享历史。
"""

from __future__ import annotations

from datetime import datetime

from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace
from animaflux.environment.scenario import FirstPresentationScenario
from animaflux.environment.life_chronicle import LifeChronicleScenario, YEAR_SECONDS
from animaflux.kernel.ids import IdGenerator
from animaflux.runtime.replay import ReplayEngine


def _influence(ids, target_state, influence_type, magnitude, created_at, metadata) -> Influence:
    return Influence(
        influence_id=ids.next(),
        source_plugin="official_demo",
        target_state=target_state,
        influence_type=influence_type,
        magnitude=magnitude,
        created_at=created_at,
        metadata=metadata,
    )


def run_demo_a() -> dict:
    """主线 A：多日 Growing Year（§12E §21-22）——世界排期演讲，生命主动准备，世界按准备度裁决。"""
    presentation_at = datetime(2000, 1, 8, 0, 0, 0)  # Day 7
    env = FirstPresentationScenario(presentation_at=presentation_at, required_preparation=2)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life(
        "demo-a",
        bootstrap=CharacterBootstrap(primary_name="小林", values=("growth", "care")),
        start_time=datetime(2000, 1, 1),
    )

    # Day 0：世界给出机会（§12E 世界塑造生命）→ opportunity → anticipation + growth need + goal
    handle.observe_text(
        "You have an exciting opportunity: give your first public presentation in one week."
    )

    # Day 1–6：无外部触发，生命主动行动（§12E 生命反作用于世界）
    agency_actions = []
    for _day in range(6):
        handle.advance(86400.0)
        outcome = handle.act()
        agency_actions.append(outcome.intent.action_type if outcome.intent else None)

    # Day 7：演讲日 → 世界解析演讲（§12E 排程外部事件）→ 成功 / 失败
    handle.advance(86400.0)
    batch = env.poll_observations(handle.now())
    handle.step(0.0, observations=batch.observations)
    presentation_success = bool(env.state.get("presentation_success"))

    if presentation_success:
        # 演讲成功 → 阅历增长：self-efficacy 的 evidence-driven 更新（§16E.4）
        ids = IdGenerator("DEMO")
        efficacy = _influence(
            ids, StateNamespace.SELF_MODEL.value, "self_model.efficacy_update", 0.6,
            handle.now(),
            {"domain": "public_speaking", "assessment": 0.65, "evidence_refs": ("ev-talk-success-1",)},
        )
        handle.step(1.0, extra_influences=(efficacy,))

    emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    efficacy_domains = [
        a.domain for a in handle.inspect(StateNamespace.SELF_MODEL).data.self_efficacy
        if a.domain == "public_speaking"
    ]

    checkpoint = handle.checkpoint()
    replay = ReplayEngine(flux.backend).replay_timeline("demo-a")

    return {
        "presentation_success": presentation_success,
        "final_preparation": env.state.get("preparation", 0),
        "agency_actions": agency_actions,
        "emotion_types": emotions,
        "self_efficacy_domains": efficacy_domains,
        "checkpoint_id": checkpoint.checkpoint_id,
        "replay_tick_count": len(replay),
    }


def run_demo_b() -> dict:
    """主线 B：关系转折 + 分支。"""
    flux = AnimaFlux()
    handle = flux.create_life("demo-b", bootstrap=CharacterBootstrap(primary_name="小林"))

    ids = IdGenerator("DEMO")

    # 建立关系：first impression（§16E.11）
    form = _influence(
        ids, StateNamespace.RELATIONSHIP.value, "relationship.form", 0.0, handle.now(),
        {
            "target_id": "human-user",
            "dimensions": {"familiarity": 0.1, "trust": 0.1, "affection": 0.05},
            "labels": ("colleague",),
        },
    )
    handle.step(1.0, extra_influences=(form,))

    # 相处：trust 增长（bounded，§13J.10）
    trust_up = _influence(
        ids, StateNamespace.RELATIONSHIP.value, "relationship.update", 0.3, handle.now(),
        {"target_id": "human-user", "dimension": "trust", "delta": 0.3},
    )
    handle.step(1.0, extra_influences=(trust_up,))

    cp = handle.checkpoint()
    base = handle.inspect(StateNamespace.RELATIONSHIP).data.relationships[0]
    base_trust = base.dimensions.trust

    # Fork 两个 Branch（§16E.13）
    branch_a = handle.branch(name="supportive")
    branch_b = handle.branch(name="conflict")

    # 分支 A：继续支持（affection 增长）
    branch_a.step((
        _influence(ids, StateNamespace.RELATIONSHIP.value, "relationship.update", 0.2, handle.now(),
                   {"target_id": "human-user", "dimension": "affection", "delta": 0.2}),
    ))
    # 分支 B：冲突（resentment 增长）
    branch_b.step((
        _influence(ids, StateNamespace.RELATIONSHIP.value, "relationship.update", 0.4, handle.now(),
                   {"target_id": "human-user", "dimension": "resentment", "delta": 0.4}),
    ))

    a_rel = branch_a.read(StateNamespace.RELATIONSHIP).relationships[0]
    b_rel = branch_b.read(StateNamespace.RELATIONSHIP).relationships[0]

    return {
        "base_trust": base_trust,
        "branch_a_id": branch_a.branch_id,
        "branch_b_id": branch_b.branch_id,
        "a_affection": a_rel.dimensions.affection,
        "b_resentment": b_rel.dimensions.resentment,
        "diverged": (a_rel.dimensions.affection != b_rel.dimensions.affection)
        or (a_rel.dimensions.resentment != b_rel.dimensions.resentment),
        "shared_prefork_trust": (a_rel.dimensions.trust == base_trust and b_rel.dimensions.trust == base_trust),
        "checkpoint_id": cp.checkpoint_id,
    }


def _seed_motivation(ids, created_at, *, goal_description: str, need_type: str) -> tuple[Influence, Influence]:
    """成对播种 goal + need（两者映射同一主动动作，无冲突，§12E）。"""
    goal = _influence(ids, StateNamespace.GOAL.value, "goal.propose", 0.6, created_at,
                      {"description": goal_description, "base_importance": 0.6, "urgency": 0.6})
    need = _influence(ids, StateNamespace.DRIVE.value, "drive.need_assess", 0.6, created_at,
                      {"need_type": need_type, "intensity": 0.5, "satisfaction": 0.5})
    return (goal, need)


def _run_lifetime(*, life_id: str, name: str, birth: datetime, seed, phase_hook=None) -> dict:
    """跑完一条生命（§12E §21-24）：出生 → 每年 advance + act → 里程碑/危机解析 → 死亡。"""
    env = LifeChronicleScenario(birth=birth)
    flux = AnimaFlux(environment=env)
    handle = flux.create_life(
        life_id, bootstrap=CharacterBootstrap(primary_name="小林", values=("growth",)), start_time=birth
    )
    handle.step(0.0, observations=(env.birth_observation(),), extra_influences=seed)

    agency_actions = []
    for _age in range(1, 81):
        handle.advance(YEAR_SECONDS)
        if phase_hook:
            phase_hook(handle, _age)
        outcome = handle.act()
        agency_actions.append(outcome.intent.action_type if outcome.intent else None)
        batch = env.poll_observations(handle.now())
        if batch.observations:
            handle.step(0.0, observations=batch.observations)
        if not env.state.get("alive", True):
            break

    emotions = [
        e.emotion_type
        for e in handle.inspect(StateNamespace.EMOTION).data.episodes
        if e.status == "active"
    ]
    return {
        "name": name,
        "death_info": env.death_info(),
        "agency_actions": agency_actions,
        "emotions": emotions,
        "chronicle": env.chronicle(),
    }


def run_demo_c() -> dict:
    """主线 C：完整一生（§12E）——同一世界，四条生命，四种死法。

    生命因「主动选择」不同（§12E 世界塑造生命，生命也反作用于世界）：
    - growth（只准备）→ 知识不足 → 45 岁病逝（早死·illness）
    - competence（只求教）→ 挺过 45，但关系不足 → 65 岁意外身亡（早死·accident）
    - safety（只联系）→ 知识不足 → 45 岁病逝（早死·illness）
    - balanced（先求教后联系，动机随人生阶段切换）→ 80 岁自然死亡
    """
    birth = datetime(2000, 1, 1)

    ids_g = IdGenerator("DEMO-G")
    growth = _run_lifetime(
        life_id="demo-c-growth", name="growth", birth=birth,
        seed=_seed_motivation(ids_g, birth, goal_description="pursue the perceived opportunity", need_type="growth"),
    )

    ids_c = IdGenerator("DEMO-C")
    competence = _run_lifetime(
        life_id="demo-c-competence", name="competence", birth=birth,
        seed=_seed_motivation(ids_c, birth, goal_description="maintain the perceived gain", need_type="competence"),
    )

    ids_s = IdGenerator("DEMO-S")
    safety = _run_lifetime(
        life_id="demo-c-safety", name="safety", birth=birth,
        seed=_seed_motivation(ids_s, birth, goal_description="avoid the perceived threat", need_type="safety"),
    )

    # balanced：phase1 用 gain goal 攒知识挺过 illness@45；phase2 完成所有旧目标（含里程碑注入的
    # loss/opportunity 目标）并换 threat goal 攒关系挺过 accident@65（人生阶段再定位，§12E §24）。
    ids_b = IdGenerator("DEMO-B")
    gain_goal = _influence(ids_b, StateNamespace.GOAL.value, "goal.propose", 0.6, birth,
                           {"description": "maintain the perceived gain", "base_importance": 0.6, "urgency": 0.6})

    def _phase_hook(handle, age: int) -> None:
        if age != 46:
            return
        goals = handle.inspect(StateNamespace.GOAL).data.goals
        completes = tuple(
            _influence(ids_b, StateNamespace.GOAL.value, "goal.complete", 0.0, handle.now(),
                       {"goal_id": g.goal_id})
            for g in goals if g.status in ("PROPOSED", "ACTIVE", "PAUSED")
        )
        threat = _influence(ids_b, StateNamespace.GOAL.value, "goal.propose", 0.6, handle.now(),
                            {"description": "avoid the perceived threat", "base_importance": 0.6, "urgency": 0.6})
        handle.step(0.0, extra_influences=completes + (threat,))

    balanced = _run_lifetime(
        life_id="demo-c-balanced", name="balanced", birth=birth, seed=(gain_goal,), phase_hook=_phase_hook,
    )

    return {"lives": [growth, competence, safety, balanced]}


def main() -> None:
    a = run_demo_a()
    print("== 主线 A：多日 Growing Year（§12E）==")
    print(f"  演讲成功           : {a['presentation_success']}")
    print(f"  最终准备度         : {a['final_preparation']}")
    print(f"  Day1–6 主动行为    : {a['agency_actions']}")
    print(f"  演讲后情绪         : {a['emotion_types']}")
    print(f"  阅历增长（自我效能）: {a['self_efficacy_domains']}")
    print(f"  Checkpoint         : {a['checkpoint_id']}")
    print(f"  可重放 Tick 数     : {a['replay_tick_count']}")

    b = run_demo_b()
    print("== 主线 B：关系转折 + 分支 ==")
    print(f"  pre-fork trust     : {b['base_trust']:.2f}")
    print(f"  分支 A（支持）     : {b['branch_a_id']} affection={b['a_affection']:.2f}")
    print(f"  分支 B（冲突）     : {b['branch_b_id']} resentment={b['b_resentment']:.2f}")
    print(f"  分支已分叉         : {b['diverged']}")
    print(f"  pre-fork 历史共享  : {b['shared_prefork_trust']}")

    c = run_demo_c()
    print("== 主线 C：完整一生（§12E）—— 同一世界，四条生命，四种死法 ==")
    for life in c["lives"]:
        d = life["death_info"]
        print(f"  [{life['name']}] 死因={d['death_cause']} 享年={d['age_at_death']} "
              f"准备={d['preparation']} 知识={d['knowledge']} 关系={d['relationship']}")
        print(f"    主动行为: {life['agency_actions']}")
        print(f"    临终情绪: {life['emotions']}")
        print("    ---- 编年史 ----")
        for line in life["chronicle"]:
            print(f"      {line}")
        print()


if __name__ == "__main__":
    main()
