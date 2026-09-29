"""
Architecture Regression Suite — 架构回归测试（文档 v5.9 §16D.39 / §16D.40）

这 10 个 invariant 是「可执行契约」：把文档里的铁律翻译成会失败的测试。
违反任何一条 = 架构漂移，直接红。它们的来源是 CLAUDE.md 的「Architecture Regression」清单。

当前状态：骨架（skip 占位）。随 P1–P4 落地，逐个移除 skip 并填实。
过 Gate（P3 / P4 / P7 / P10）前，对应 invariant 必须已激活且绿。

使用方式：
  1. 到达对应阶段，删掉该测试的 @pytest.mark.skip 行；
  2. 用 TODO 处写真实断言；
  3. 确保 `pytest tests/architecture/` 全绿再进下一阶段。
"""

import pytest

# TODO(P0): 项目骨架建立后，这里 import 真实模块
# from animaflux import ...  # 目前 src/animaflux 尚未建立


# ---------------------------------------------------------------------------
# 1. Owner isolation — 文档 §3.10 / §16D.3
# ---------------------------------------------------------------------------
def test_owner_isolation():
    """非 Owner 不能直接写 State；跨模块改变只能走 Influence，经 Resolver 到 Owner。"""
    from datetime import datetime, timedelta

    from animaflux.contracts.context import ExecutionContext, TimeContext
    from animaflux.contracts.influence import Influence
    from animaflux.contracts.state import StateNamespace, StateResolutionResult
    from animaflux.kernel.random import RandomService
    from animaflux.kernel.registry import CapabilityRegistry, NamespaceRegistry
    from animaflux.runtime.context import RuntimeContextImpl
    from animaflux.runtime.resolver import StateResolver
    from animaflux.state.state_store import StateStore

    def ctx() -> RuntimeContextImpl:
        return RuntimeContextImpl(
            execution=ExecutionContext(
                runtime_id="r", agent_id="a", tick_id="t1",
                plugin_id="p", process_id="pr", phase="test",
            ),
            time=TimeContext(world_time=datetime(2000, 1, 1), delta_time=timedelta(seconds=1)),
            random=RandomService(root_seed=0),
            capabilities=CapabilityRegistry(),
        )

    registry = NamespaceRegistry()
    store = StateStore("agent-1", registry=registry)
    store.seed(StateNamespace.EMOTION, {"joy": 0.5})
    store.seed(StateNamespace.BODY, {"energy": 1.0})

    calls = {"emotion": [], "body": []}

    class Owner:
        def __init__(self, ns):
            self.ns = ns

        def resolve(self, current_state, influences, context):
            calls[self.ns].append(influences)
            return StateResolutionResult(next_state=current_state, changed=False)

    emotion_owner = Owner("emotion")
    body_owner = Owner("body")
    registry.register_owner(StateNamespace.EMOTION, emotion_owner)
    registry.register_owner(StateNamespace.BODY, body_owner)

    # (1) 非 Owner 直接写另一 Namespace 的状态 → 被拒绝
    store.begin_tick()
    with pytest.raises(PermissionError):
        store.stage(StateNamespace.EMOTION, {"joy": 0.9}, owner=body_owner)

    # (2) 跨模块改变只能走 Influence → Resolver → 目标 Namespace 的 Primary Owner
    inf = Influence(
        influence_id="INF-001",
        source_plugin="body_owner",
        target_state="emotion",
        influence_type="social_support",
        magnitude=0.4,
        created_at=datetime(2000, 1, 1),
    )
    resolver = StateResolver(store, registry)
    outcome = resolver.resolve([inf], ctx())
    assert outcome.ok
    assert calls["emotion"] == [(inf,)]
    assert calls["body"] == []


# ---------------------------------------------------------------------------
# 2. Capability immutability — 文档 §9.15 / §16D.7
# ---------------------------------------------------------------------------
def test_capability_immutability():
    """Capability 返回 immutable View/DTO，不返回内部 State；外部改不动。"""
    from dataclasses import FrozenInstanceError, dataclass

    from animaflux.contracts.state import StateNamespace
    from animaflux.state.state_read import StateReadCapability
    from animaflux.state.state_store import StateStore

    @dataclass(frozen=True)
    class EmotionState:
        joy: float = 0.5

    store = StateStore("agent-1")
    store.seed(StateNamespace.EMOTION, EmotionState(joy=0.5))

    cap = StateReadCapability(store)
    view = cap.get_state(StateNamespace.EMOTION)

    # View 本身 frozen：字段改不动
    with pytest.raises(FrozenInstanceError):
        view.version = 999
    with pytest.raises(FrozenInstanceError):
        view.data = {"x": 1}
    # 底层 state 也是 frozen：嵌套字段同样改不动
    with pytest.raises(FrozenInstanceError):
        view.data.joy = 0.9


# ---------------------------------------------------------------------------
# 3. Transaction rollback — 文档 §19 / §16D.14
# ---------------------------------------------------------------------------
def test_transaction_rollback():
    """Tick 中途失败 → Rollback，不留 committed version，Current Pointer 不推进。"""
    from animaflux.contracts.persistence import StateVersionRecord
    from animaflux.persistence.inmemory import InMemoryBackend
    from animaflux.runtime.transaction import TickCommitError, TransactionCoordinator

    class FailOnCurrent:
        """注入 current pointer 发布失败（§16D.14）。"""

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def write_current(self, *args, **kwargs):
            raise RuntimeError("current pointer publish failure")

    def version(svid, rev, parent=None):
        return StateVersionRecord(
            state_version_id=svid, agent_id="a", namespace="emotion",
            revision=rev, payload={"joy": rev / 10}, parent_version_id=parent,
        )

    backend = InMemoryBackend()
    # 先成功提交 t1：seed emotion_v1 + current pointer
    TransactionCoordinator(backend).commit_tick(
        agent_id="a", tick_id="t1", commit_id="C1",
        new_versions=[version("emotion_v1", 1)],
        version_map={"emotion": "emotion_v1"},
    )
    assert backend.read_current("a", "emotion") == "emotion_v1"

    # t2：v2 已写入后才在 current pointer 发布处失败 → 必须整体回滚
    failing = TransactionCoordinator(FailOnCurrent(backend))
    with pytest.raises(TickCommitError):
        failing.commit_tick(
            agent_id="a", tick_id="t2", commit_id="C2",
            new_versions=[version("emotion_v2", 2, parent="emotion_v1")],
            version_map={"emotion": "emotion_v2"},
        )

    # 无半提交生命状态：v2 被回滚，旧指针仍是权威（§19.10 / §16D.14）
    assert backend.read_current("a", "emotion") == "emotion_v1"
    assert backend.read_version("emotion_v2") is None
    assert backend.read_version("emotion_v1") is not None
    assert backend.read_commit("C2") is None


# ---------------------------------------------------------------------------
# 4. Replay exactness — 文档 §21 / §22.9 / §16D.17
# ---------------------------------------------------------------------------
def test_replay_exactness():
    """Exact Replay 不产生新 state/event/memory，且永不回拨历史 LLM。"""
    from datetime import datetime

    from animaflux.contracts.influence import Influence
    from animaflux.contracts.state import StateNamespace
    from animaflux.persistence.inmemory import InMemoryBackend
    from animaflux.plugins.default_life import register_default_life
    from animaflux.plugins.default_life.body import BodyState
    from animaflux.plugins.default_life.emotion import (
        INFLUENCE_TRIGGER,
        EmotionState,
        serialize as emotion_serialize,
    )
    from animaflux.plugins.default_life.identity import IdentityState
    from animaflux.runtime.lifeloop import LifeRuntime
    from animaflux.runtime.replay import ReplayEngine

    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())

    trigger = Influence(
        influence_id="EXT-1", source_plugin="test", target_state="emotion",
        influence_type=INFLUENCE_TRIGGER, magnitude=0.7, created_at=runtime.now(),
        metadata={"emotion_type": "joy", "valence": 0.8, "arousal": 0.6},
    )
    runtime.step(60.0, extra_influences=(trigger,))  # t1：emotion 变化
    runtime.step(60.0)                                # t2：emotion 继续衰减变化

    backend = runtime.backend
    versions_before = set(backend._versions.keys())
    commits_before = set(backend._commits.keys())

    engine = ReplayEngine(backend)
    ticks = engine.replay_timeline("agent-1")

    # 永不回拨 LLM / 只读（§21.1 / §21.3 / §22.9）
    assert engine.llm_calls == 0
    assert engine.write_ops == 0
    # 不产生新 State Version / Commit（§21.2）
    assert set(backend._versions.keys()) == versions_before
    assert set(backend._commits.keys()) == commits_before

    # 结果与历史一致：最后一条 emotion 回放 payload 等于当前 serialized 状态（§16D.17）
    current_payload = emotion_serialize(runtime.read(StateNamespace.EMOTION))
    emotion_ticks = [t for t in ticks if "emotion" in t.payloads and t.tick_id != "t0"]
    assert emotion_ticks, "期望至少一个 emotion 变化的 tick"
    assert emotion_ticks[-1].payloads["emotion"] == current_payload


# ---------------------------------------------------------------------------
# 5. Branch isolation — 文档 §21 / §16D.19
# ---------------------------------------------------------------------------
def test_branch_isolation():
    """Branch 共享 pre-fork 历史，post-fork 演化相互独立、互不污染。"""
    from datetime import datetime

    from animaflux.contracts.influence import Influence
    from animaflux.contracts.state import StateNamespace
    from animaflux.persistence.inmemory import InMemoryBackend
    from animaflux.plugins.default_life import register_default_life
    from animaflux.plugins.default_life.body import BodyState
    from animaflux.plugins.default_life.emotion import INFLUENCE_TRIGGER, EmotionState
    from animaflux.plugins.default_life.identity import IdentityState
    from animaflux.runtime.branch import fork
    from animaflux.runtime.lifeloop import LifeRuntime

    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())

    checkpoint = runtime.checkpoint()
    branch_a = fork(checkpoint, registry=runtime.registry, branch_name="A")
    branch_b = fork(checkpoint, registry=runtime.registry, branch_name="B")

    t = datetime(2000, 1, 1, 1)

    def joy(iid, valence):
        return Influence(
            influence_id=iid, source_plugin="test", target_state="emotion",
            influence_type=INFLUENCE_TRIGGER, magnitude=0.7, created_at=t,
            metadata={"emotion_type": "joy", "valence": valence, "arousal": 0.6},
        )

    branch_a.step([joy("A-1", 0.8)])
    branch_b.step([joy("B-1", -0.6)])

    # post-fork 独立：一支的正向情绪不影响另一支的负向情绪（§21.8）
    assert branch_a.read(StateNamespace.EMOTION).episodes[0].valence > 0
    assert branch_b.read(StateNamespace.EMOTION).episodes[0].valence < 0
    assert branch_a.read(StateNamespace.EMOTION) != branch_b.read(StateNamespace.EMOTION)

    # pre-fork 共享：两分支指向同一个 fork checkpoint（§21.6 / §21.9）
    assert branch_a.record.fork_checkpoint_id == checkpoint.checkpoint_id
    assert branch_b.record.fork_checkpoint_id == checkpoint.checkpoint_id
    assert branch_a.record.parent_branch_id is None
    assert branch_a.record.random_mode == "deterministic"


# ---------------------------------------------------------------------------
# 6. Knowledge boundary — 文档 §13F.25 / §14E / §16D.11
# ---------------------------------------------------------------------------
def test_knowledge_boundary():
    """Agent 不能陈述从未感知/记忆的事实；「不知道」≠「不记得」。"""
    from animaflux.contracts.memory import MemoryRetrievalRequest
    from animaflux.memory.memory_store import MemoryStore
    from animaflux.memory.retrieval import MemoryRetrievalCapability

    # Agent 只能检索自己形成过的 Memory，不能把 Objective 事实当自身记忆（§13F.25 / §14C.19）

    # 1) 「不知道」：查询 Agent 从未经历的事实 → 检索不到，不编造
    store = MemoryStore("agent-1")
    store.form("episodic", "我昨晚在家读书", source_refs=("EVT-1",))
    cap = MemoryRetrievalCapability(store)
    unknown = cap.retrieve(MemoryRetrievalRequest(query="皇帝遇刺", memory_count_budget=10))
    assert not any("皇帝" in str(m.content) for m in unknown.memories)

    # 2) 「不记得」：记得过但 accessibility 衰减 → Stored ≠ Retrievable，且内容仍在（非删除）
    store2 = MemoryStore("agent-2")
    mid = store2.form("episodic", "我见过老王", source_refs=("EVT-2",))
    store2.decay_accessibility(mid, factor=0.01)
    cap2 = MemoryRetrievalCapability(store2)
    forgotten = cap2.retrieve(MemoryRetrievalRequest(query="老王", min_accessibility=0.1))
    assert not any("老王" in str(m.content) for m in forgotten.memories)
    assert store2.get_current_version(mid) is not None  # 记忆仍在

    # 3) 记得的 → 检索得到（FOUND）
    found = cap.retrieve(MemoryRetrievalRequest(query="读书", memory_count_budget=10))
    assert any("读书" in str(m.content) for m in found.memories)


# ---------------------------------------------------------------------------
# 7. LLM retry reuse — 文档 §15D.22 / §23.14 / §16D.16
# ---------------------------------------------------------------------------
def test_llm_retry_reuse():
    """技术 Retry 复用已记录的非确定结果，不重复计费/重复调用。"""
    from animaflux.llm.call_strategy import LLMCallRequest, LLMCallStrategy

    calls = {"n": 0}

    class Provider:
        name = "fake-provider"

        def generate(self, request_input):
            calls["n"] += 1
            return {"text": f"thought-{calls['n']}"}

    strategy = LLMCallStrategy(Provider(), model="test")
    request = LLMCallRequest(
        logical_call_id="LOGIC-1",
        process_id="decision",
        prompt_template_id="tpl-1",
        prompt_version="v1",
        input={"goal": "present"},
    )

    first = strategy.call(request)
    # 技术重试：同一 logical_call_id 复用已成功结果，不重复调用 provider（§15D.22）
    second = strategy.call(request)

    assert first.status == "SUCCEEDED"
    assert first.result == second.result
    assert first.logical_call_id == second.logical_call_id
    assert calls["n"] == 1
    assert strategy.provider_calls == 1


# ---------------------------------------------------------------------------
# 8. External action idempotency — 文档 §12C / §15B.17 / §16D.15
# ---------------------------------------------------------------------------
def test_external_action_idempotency():
    """外部副作用（非 SQLite 可回滚）必须 Journal 化，支持技术 Retry 复用且幂等。"""
    from datetime import datetime

    from animaflux.contracts.environment import ActionIntent, ActionResult
    from animaflux.environment.action_journal import ExternalActionJournal

    side_effects = {"n": 0}

    class Environment:
        def submit_action(self, intent):
            side_effects["n"] += 1
            return ActionResult(
                result_id=f"R{side_effects['n']}",
                intent_id=intent.intent_id,
                status="success",
                world_time=datetime(2000, 1, 1),
            )

    journal = ExternalActionJournal(Environment())
    intent = ActionIntent(
        intent_id="ACT-1", actor="agent-1", action_type="send_message",
        world_time=datetime(2000, 1, 1), content="hi",
    )

    r1 = journal.submit(intent)
    # 技术重试：同一 action_id 幂等复用，不重复执行外部副作用（§15B.17）
    r2 = journal.submit(intent)

    assert r1.result_id == r2.result_id
    assert side_effects["n"] == 1
    assert journal.executed_count() == 1


# ---------------------------------------------------------------------------
# 9. Memory versioning — 文档 §13F / §16B.14 / §16D.13
# ---------------------------------------------------------------------------
def test_memory_versioning():
    """Memory 出新版本不覆盖；Forgetting ≠ Delete；Reconsolidation 产生新版本。"""
    from animaflux.memory.memory_store import MemoryStore

    store = MemoryStore("agent-1")
    mid = store.form("episodic", "原始记忆", importance=0.7, source_refs=("EVT-1",))
    v1 = store.get_current_version(mid)
    assert v1.revision == 1

    # Reconsolidation → 新版本，Current 指针指向新版本（§16B.14）
    store.reconsolidate(mid, content="重新解释后的记忆", confidence=0.8)
    v2 = store.get_current_version(mid)
    assert v2.revision == 2
    assert v2.content == "重新解释后的记忆"
    assert v2.parent_version_id == v1.memory_version_id

    # 旧版本仍在（copy-on-write，不覆盖，§13F.18）
    versions = store.list_versions(mid)
    assert len(versions) == 2
    assert store.get_version(v1.memory_version_id).content == "原始记忆"

    # Forgetting = accessibility decay，不是 delete（§13F.15）
    store.decay_accessibility(mid, factor=0.5)
    assert store.get_current_version(mid) is not None  # 记忆内容仍在
    assert store.get_entry(mid).status == "active"  # 没被删
    assert store.current_runtime_state(mid).accessibility < 1.0


# ---------------------------------------------------------------------------
# 10. Development Context — 文档 Cross-cutting §1–§24 / §16D.5
# ---------------------------------------------------------------------------
def test_development_context():
    """Age ≠ Experience ≠ Skill ≠ Self-Efficacy；禁止全局 age_multiplier。"""
    from datetime import datetime

    from animaflux.runtime.development import DevelopmentContextBuilder

    view = DevelopmentContextBuilder().build(
        agent_id="a",
        birth_time=datetime(1980, 1, 1),
        runtime_time=datetime(2000, 1, 1),
    )
    # 年龄是 timedelta，独立于阅历；life_stage 由可替换策略派生（§24.3 / §24.5）
    assert view.chronological_age.days > 0
    assert view.life_stage == "adulthood"
    # 禁止全局 experience_level / age_multiplier（§24.7 / §24.16）
    assert not hasattr(view, "experience_level")
    assert not hasattr(view, "age_multiplier")
    # 阅历是 domain-specific 的 ExperienceProfileView，不压成单一全局值（§24.7 / §24.8）
    assert view.domain_experience is not None


# ===========================================================================
# 长期保留的三条（文档 §19 / §16D.27）—— 与上面 10 条并列，永远不能删
# ===========================================================================
def _experience_profile(agent_id: str, domain: str, n: int):
    from animaflux.memory.experience import ExperienceIndex
    from animaflux.memory.memory_store import MemoryStore

    store = MemoryStore(agent_id)
    for i in range(n):
        store.form("episodic", f"event {i}", domain=domain, importance=0.6)
    index = ExperienceIndex()
    index.rebuild(store.iter_current_memories())
    return index.profile()


def test_same_age_different_experience():
    """Same Age, Different Experience → 同一事件产生不同认知（§16D.27）。"""
    from datetime import datetime

    from animaflux.contracts.appraisal import AppraisableItem
    from animaflux.plugins.default_cognition.appraisal import AppraisalProcess
    from animaflux.runtime.development import DevelopmentContextBuilder

    birth = datetime(1980, 1, 1)
    now = datetime(2000, 1, 1)
    builder = DevelopmentContextBuilder()

    novice = builder.build(
        agent_id="novice", birth_time=birth, runtime_time=now,
        domain_experience=_experience_profile("novice", "public_speaking", 0),
    )
    expert = builder.build(
        agent_id="expert", birth_time=birth, runtime_time=now,
        domain_experience=_experience_profile("expert", "public_speaking", 12),
    )

    item = AppraisableItem(
        item_ref="E1", item_type="perceived_event",
        content={"domain": "public_speaking", "text": "give a presentation"},
        salience=0.9,
    )
    proc = AppraisalProcess()
    novice_result = proc.appraise([item], development=novice)[0]
    expert_result = proc.appraise([item], development=expert)[0]

    # 同年龄
    assert novice.chronological_age == expert.chronological_age
    # 阅历不同 → 认知不同（领域阅历越高 novelty 越低，§24.20）
    assert novice_result.novelty > expert_result.novelty


def test_different_age_same_experience():
    """Different Age, Same Relevant Experience → 不得自动刻板化（§24 原则 10）。"""
    from datetime import datetime

    from animaflux.contracts.appraisal import AppraisableItem
    from animaflux.plugins.default_cognition.appraisal import AppraisalProcess
    from animaflux.runtime.development import DevelopmentContextBuilder

    builder = DevelopmentContextBuilder()
    young = builder.build(
        agent_id="young", birth_time=datetime(1980, 1, 1), runtime_time=datetime(2000, 1, 1),
        domain_experience=_experience_profile("young", "public_speaking", 6),
    )
    old = builder.build(
        agent_id="old", birth_time=datetime(1930, 1, 1), runtime_time=datetime(2000, 1, 1),
        domain_experience=_experience_profile("old", "public_speaking", 6),
    )

    item = AppraisableItem(
        item_ref="E1", item_type="perceived_event",
        content={"domain": "public_speaking", "text": "give a presentation"},
        salience=0.9,
    )
    proc = AppraisalProcess()
    young_result = proc.appraise([item], development=young)[0]
    old_result = proc.appraise([item], development=old)[0]

    # 年龄不同，但同一领域阅历相同 → 该领域 appraisal novelty 相同，不因裸 age 刻板化
    assert young.chronological_age < old.chronological_age
    assert young_result.novelty == old_result.novelty
    # 年龄仍经可替换 LifeStagePolicy 正确体现（不写死，§24.5）
    assert young.life_stage != old.life_stage


def test_experience_not_competence_not_self_efficacy():
    """Experience ≠ Competence ≠ Self-Efficacy：经验多不保证更正确/更冷静。"""
    from animaflux.contracts.experience import DomainExperience
    from animaflux.plugins.default_life.self_model import SelfAspect, SelfModelState

    # 阅历高（exposure 大）
    experience = DomainExperience(domain="public_speaking", exposure=50)
    # 但 self-efficacy 可以独立地低（我认为自己不会），两者不合并（§24 原则 6）
    efficacy = SelfAspect(domain="public_speaking", dimension="self_efficacy", assessment=0.2)
    state = SelfModelState(self_efficacy=(efficacy,))

    # Experience 没有 competence / self_efficacy 字段，三者是独立概念
    assert not hasattr(experience, "competence")
    assert not hasattr(experience, "self_efficacy")
    # 高阅历 + 低自我效能可以并存（独立存储，互不派生）
    assert experience.exposure == 50
    assert state.self_efficacy[0].assessment == 0.2
