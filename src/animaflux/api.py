"""Public API（v5.9 §16C）。

小型 Facade：用户表达「想对这个数字生命做什么」，而不是「Runtime 内部如何实现」。
三层：Life User API（AnimaFlux / LifeHandle）、Inspection（只读 View）、Plugin Dev。
隐藏 StateResolver / StateOwner / StateStore / Transaction 等内部机制（§16C）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from animaflux.contracts.environment import AgencyOutcome, Observation
from animaflux.contracts.influence import Influence
from animaflux.contracts.memory import MemoryRetrievalRequest
from animaflux.contracts.state import StateNamespace
from animaflux.contracts.summary import HomeostasisSummary, LifeSummaryView, MoodSummary
from animaflux.contracts.turn import TurnResult
from animaflux.environment.life_chronicle import LifeChronicleScenario
from animaflux.environment.scenario import FirstPresentationScenario
from animaflux.kernel.ids import IdGenerator
from animaflux.llm.call_strategy import LLMCallStrategy
from animaflux.llm.providers import SiliconFlowProvider
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.persistence.sqlite import SqliteBackend
from animaflux.plugins.default_life import (
    belief,
    body,
    drive,
    emotion,
    goal,
    identity,
    narrative,
    personality,
    relationship,
    register_default_life,
    self_model,
    value,
    world_model,
)
from animaflux.plugins.default_life._common import clamp01, from_iso
from animaflux.plugins.default_life.belief import BeliefState
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.drive import DriveState
from animaflux.plugins.default_life.emotion import EmotionState
from animaflux.plugins.default_life.goal import GoalState
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.plugins.default_life.narrative import NarrativeState
from animaflux.plugins.default_life.personality import CORE_TRAITS, PersonalityState, Trait
from animaflux.plugins.default_life.relationship import RelationshipState
from animaflux.plugins.default_life.self_model import SelfModelState
from animaflux.plugins.default_life.value import ValueCommitment, ValueState
from animaflux.plugins.default_life.world_model import WorldModelState
from animaflux.runtime.branch import LifeBranch, fork
from animaflux.runtime.checkpoint import Checkpoint
from animaflux.runtime.development import DevelopmentContextBuilder
from animaflux.runtime.lifeloop import LifeRuntime
from animaflux.runtime.replay import ReplayEngine, ReplayedTick
from animaflux.state.state_read import StateReadCapability

_DESERIALIZE = {
    "identity": identity.deserialize,
    "body": body.deserialize,
    "personality": personality.deserialize,
    "emotion": emotion.deserialize,
    "drive": drive.deserialize,
    "belief": belief.deserialize,
    "value": value.deserialize,
    "goal": goal.deserialize,
    "relationship": relationship.deserialize,
    "world_model": world_model.deserialize,
    "self_model": self_model.deserialize,
    "narrative": narrative.deserialize,
}


@dataclass(frozen=True)
class CharacterBootstrap:
    """Character Bootstrap（§16C.5）：这个生命最初是谁，与 Runtime Config 分离。"""

    primary_name: str = "小林"
    birth_time: datetime | None = None
    traits: dict[str, float] | None = None
    values: tuple[str, ...] = ()


# 世界时间锚点：Web 建生命不传 start_time，Runtime 时钟从 2000-01-01 起（create_life），
# 场景锚点必须与之对齐（§12E）。
_WORLD_EPOCH = datetime(2000, 1, 1)


def build_scenario_environment(scenario: str):
    """按场景名构建内置演示环境（§12E），返回 `(env, scenario_type)`。

    - "presentation" → FirstPresentationScenario（多日演讲，7 天后裁决成败）
    - "chronicle"    → LifeChronicleScenario（80 年压缩一生，出生即世界时间锚点）
    - 其它 / 空       → (None, None)（无世界，与现状一致）

    World 是进程内内存态：外部世界事实，非 Core State、不进 StateStore、不持久化（§12E 铁律）。
    这是 Public Facade 暴露给 Web 的合法入口，避免 Web 穿透 Core 内部（§Web Plan §2/§10）。
    """
    scenario = (scenario or "").strip().lower()
    if scenario == "presentation":
        return FirstPresentationScenario(presentation_at=_WORLD_EPOCH + timedelta(days=7)), "presentation"
    if scenario == "chronicle":
        return LifeChronicleScenario(birth=_WORLD_EPOCH), "chronicle"
    return None, None


class AnimaFlux:
    """应用级框架入口（§16C.2）。v0.1 默认 InMemory 后端 + 确定性（No-LLM）。

    LLM 是可选 Cognitive Capability（§15D.1）：传入 `llm`（LLMCallStrategy）或经
    `from_config` 的 `llm` 配置启用；不配置时全部走确定性 fallback（Deterministic First）。
    """

    def __init__(
        self,
        backend=None,
        *,
        llm: LLMCallStrategy | None = None,
        environment=None,  # §12E：可选环境插头，供 LifeHandle.act() 使用
    ) -> None:
        self.backend = backend or InMemoryBackend()
        self.llm = llm
        self.environment = environment

    @classmethod
    def from_config(cls, config: dict | None = None) -> "AnimaFlux":
        """从配置构造。`config["llm"]` 支持 `{"provider": "siliconflow", "api_key", "model"}`；
        缺省 `api_key` 时从环境变量读取。`config["backend"]` 支持：
          - 省略 → InMemory（默认）
          - 一个 PersistenceBackend 实例 → 原样使用
          - dict `{"type": "sqlite"|"memory", "path": ...}`（§Web Plan §6）
          - 字符串 `"sqlite:<path>"` / `"memory"` / 裸路径
        未配置 `llm` 则确定性运行。"""
        config = config or {}
        backend = _build_backend(config.get("backend"))
        llm_cfg = config.get("llm")
        llm = _build_llm(llm_cfg) if llm_cfg else None
        return cls(backend=backend, llm=llm)

    def create_life(
        self,
        agent_id: str = "life-1",
        *,
        bootstrap: CharacterBootstrap | dict | None = None,
        start_time: datetime | None = None,
        environment=None,
    ) -> "LifeHandle":
        """创建数字生命并隐藏 13 Core State 初始化细节（§16C.4）。

        `environment`（§12E）可选；缺省继承 `self.environment`。Web 每生命独立 world 时按需传入。
        """
        boot = _as_bootstrap(bootstrap)
        runtime = LifeRuntime(
            agent_id,
            self.backend,
            start_time=start_time or datetime(2000, 1, 1),
            llm=self.llm,
            environment=self.environment if environment is None else environment,
        )
        register_default_life(runtime)
        runtime.seed(
            StateNamespace.IDENTITY,
            IdentityState(birth_time=boot.birth_time or datetime(1980, 1, 1), primary_name=boot.primary_name),
        )
        runtime.seed(StateNamespace.BODY, BodyState())
        runtime.seed(StateNamespace.EMOTION, EmotionState())
        traits = boot.traits or {}
        trait_tuple = tuple(
            Trait(name=name, value=clamp01(traits.get(name, 0.5))) for name in CORE_TRAITS
        )
        runtime.seed(StateNamespace.PERSONALITY, PersonalityState(traits=trait_tuple))
        commitments = tuple(
            ValueCommitment(value_id=f"V{i + 1}", value_type=v) for i, v in enumerate(boot.values)
        )
        runtime.seed(StateNamespace.VALUE, ValueState(commitments=commitments))
        runtime.seed(StateNamespace.RELATIONSHIP, RelationshipState())
        runtime.seed(StateNamespace.SELF_MODEL, SelfModelState())
        # P8：Motivation & Social Cognition 进入生命切片（§13E/§13G/§13I）。
        runtime.seed(StateNamespace.DRIVE, DriveState())
        runtime.seed(StateNamespace.BELIEF, BeliefState())
        runtime.seed(StateNamespace.GOAL, GoalState())
        # P9：Slow Self Development 进入生命切片（§13C/§13H/§13L/§13M + §14F）。
        # Narrative / World Model 以空态 seed（Reflection 低频沉淀；World Model 依赖 belief_refs，
        # v0.1 留空待 P10 结构化集成）。
        runtime.seed(StateNamespace.NARRATIVE, NarrativeState())
        runtime.seed(StateNamespace.WORLD_MODEL, WorldModelState())
        return LifeHandle(runtime, agent_id=agent_id)

    def restore(self, checkpoint: Checkpoint, *, environment=None) -> "LifeHandle":
        """RESTORE：延续原生命（§16C.14 / §16C.15），不创建新 branch_id。

        以 Checkpoint 的不可变状态快照为种子重建一个新 Runtime 继续演化；v0.1 用独立后端
        承载，与 `open()`（同一持久化后端内延续）互补。
        """
        runtime = LifeRuntime(
            checkpoint.agent_id,
            InMemoryBackend(),
            llm=self.llm,
            environment=self.environment if environment is None else environment,
        )
        register_default_life(runtime)
        for ns_value, state in checkpoint.states.items():
            runtime.seed(StateNamespace(ns_value), state)
        return LifeHandle(runtime, agent_id=checkpoint.agent_id)

    def open(self, agent_id: str, *, environment=None) -> "LifeHandle":
        """RESTORE：从持久化后端加载最新已提交状态继续原 agent（§16C.14）。

        `environment` 可选（§12E）；缺省继承 `self.environment`。Web 重新打开带 world 的生命时
        传入其进程内场景实例，以复用同一世界事实。
        """
        current = self.backend.list_current(agent_id)
        commits = self.backend.list_commits(agent_id)
        start_time = None
        if commits and commits[-1].runtime_time_after:
            start_time = from_iso(commits[-1].runtime_time_after)
        runtime = LifeRuntime(
            agent_id,
            self.backend,
            start_time=start_time,
            llm=self.llm,
            environment=self.environment if environment is None else environment,
        )
        register_default_life(runtime)
        for ns_value, version_id in current.items():
            deserialize = _DESERIALIZE.get(ns_value)
            if deserialize is None:
                continue
            rec = self.backend.read_version(version_id)
            if rec is None or rec.payload is None:
                continue
            runtime.load_committed(StateNamespace(ns_value), rec.revision, deserialize(rec.payload))
        runtime.resume_tick(_last_tick_number(commits))
        return LifeHandle(runtime, agent_id=agent_id)

    def list_lives(self) -> tuple[str, ...]:
        """列出已持久化的所有生命 id（只读 Public Facade，§Web Plan §10）。"""
        return tuple(self.backend.list_agents())

    def delete_life(self, agent_id: str) -> None:
        """永久删除一条生命（§Web Plan §10）：移除其全部持久化历史与当前指针。"""
        self.backend.delete_agent(agent_id)


class LifeHandle:
    """单生命安全操作入口（§16C.3 / §16C.4）。"""

    def __init__(self, runtime: LifeRuntime, *, agent_id: str) -> None:
        self._runtime = runtime
        self.agent_id = agent_id
        self.branch_id = "main"
        self._branch_ids = IdGenerator("BR", width=None)
        self._obs_ids = IdGenerator("OBS", width=None)
        # v0.1 进程内跟踪 Checkpoint / Branch（§Web Plan §7/§14）；持久化列表随 P10 补齐。
        self._checkpoints: list[Checkpoint] = []
        self._branches: list["LifeBranchHandle"] = []

    # -- 生命周期（§16C.6） --
    def step(
        self,
        delta_seconds: float,
        *,
        observations: tuple[Observation, ...] = (),
        extra_influences: tuple[Influence, ...] = (),
    ) -> str:
        return self._runtime.step(
            delta_seconds, observations=observations, extra_influences=extra_influences
        )

    def advance(self, delta_seconds: float) -> str:
        """推进 World Time（§16C.6）；v0.1 压缩为一个 Tick。"""
        return self._runtime.step(delta_seconds)

    def advance_world(self, delta_seconds: float) -> str:
        """推进时间并把「推进后到期」的世界排程事件一并回灌（单 Tick，§12E）。

        无 environment 时等价 `advance`；有则用推进后的时间 `poll_observations`，把世界事件作为
        observations 交给**一次** `step(delta)`——推进与感知发生在同一 Tick，不再产生空推进。
        """
        env = self._runtime.environment
        if env is None:
            return self._runtime.step(delta_seconds)
        future = self.now() + timedelta(seconds=delta_seconds)
        batch = env.poll_observations(future)
        return self._runtime.step(delta_seconds, observations=batch.observations)

    def world_view(self) -> dict | None:
        """只读世界事实视图（§12E）：外部世界事实，非 Core State。

        无 environment 时返回 None；有则返回 facts（dict 拷贝）并鸭子类型探测 chronicle() /
        death_info()（完整一生场景）追加。
        """
        env = self._runtime.environment
        if env is None:
            return None
        view: dict = {"facts": dict(env.state.facts)}
        if hasattr(env, "chronicle"):
            view["chronicle"] = list(env.chronicle())
        if hasattr(env, "death_info"):
            view["death_info"] = env.death_info()
        return view

    def observe(self, observation: Observation) -> str:
        """通用外部输入（§16C.7），不能直接改 State。"""
        return self._runtime.step(1.0, observations=(observation,))

    def observe_text(self, text: str) -> str:
        """通用外部观察输入的文本便捷入口（§16C.7）：包装成 Observation 走完整认知。"""
        obs = Observation(
            observation_id=self._obs_ids.next(),
            modality="observation",
            content=text,
            world_time=self.now(),
            clarity=1.0,
            intensity=0.5,
            source_entity="human",
        )
        return self._runtime.step(1.0, observations=(obs,))

    def send_text(self, text: str, *, delta_seconds: float = 1.0) -> TurnResult:
        """Human 对话（§16C.8）：完整 Cognition，绝不等于 llm.chat()。"""
        return self._runtime.send_text(text, delta_seconds=delta_seconds)

    def reflect_now(self) -> str:
        """显式触发 Reflection（§14F.1）：把累计的显著经历反思成慢状态更新并 Durable Commit。"""
        return self._runtime.reflect_now()

    def act(self, *, delta_seconds: float = 0.0) -> AgencyOutcome:
        """一次「主动决策机会」（§12E）：无外部触发，由内部动机驱动行动并反作用于世界。

        需要 AnimaFlux(environment=...) 已配置；否则抛 RuntimeError。返回 AgencyOutcome
        （acted / decision / intent / action_result / tick_id）。
        """
        return self._runtime.act(delta_seconds=delta_seconds)

    def agency_log(self) -> tuple[dict, ...]:
        """主动决策的「为什么」叙事（§12E A8），只读序列化视图。"""
        return tuple(
            {
                "decision_id": r.decision_id,
                "world_time": r.world_time.isoformat(),
                "trigger_type": r.trigger_type,
                "relevant_goal_refs": list(r.relevant_goal_refs),
                "motivation_refs": list(r.motivation_refs),
                "selected_action_type": r.selected_action_type,
                "initiative": r.initiative,
                "expected_outcome": r.expected_outcome,
                "confidence": r.confidence,
                "no_action_reason": r.no_action_reason,
            }
            for r in self._runtime.agency_log()
        )

    def diary(self) -> tuple[dict, ...]:
        """日记列表（Narrative 的对外呈现，§13M）：只读视图，新在前。"""
        return self._runtime.diary_entries()

    def write_diary(self, *, topic: str | None = None, time_start=None, time_end=None) -> dict:
        """点击写日记：按话题 / 时间段取上下文 → 合成第一人称散文 → narrative.add_chapter。

        time_start / time_end 接受 datetime 或 ISO 字符串，皆可空。返回新写入的章节视图
        （chapter_id / title / time / summary / memory_refs / committed）。
        """
        return self._runtime.write_diary(
            topic=topic,
            time_start=self._coerce_time(time_start),
            time_end=self._coerce_time(time_end),
        )

    @staticmethod
    def _coerce_time(value):
        """把 ISO 字符串宽容转成 datetime，datetime / None 原样返回（供 write_diary 时间窗）。"""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            return datetime.fromisoformat(value)
        return value

    # -- Inspection（§16C.11 / §16C.12） --
    def inspect(self, namespace: StateNamespace):
        """只读 Inspection，返回 immutable View，不返回可变内部 State（§16C.11）。"""
        return StateReadCapability(self._runtime.store).get_state(namespace)

    def state_overview(self) -> tuple[dict, ...]:
        """13 Core State 的只读概览（§Web Plan §12.4/§39.14）：namespace + seeded + version。

        未 seed 的 Namespace（当前生命切片尚未初始化）以 seeded=False 呈现，前端据此省略/标记。
        """
        committed = set(self._runtime.store.committed_namespaces())
        out = []
        for ns in StateNamespace:
            seeded = ns in committed
            version = None
            if seeded:
                version = self._runtime.store.committed_version(ns).version
            out.append({"namespace": ns.value, "seeded": seeded, "version": version})
        return tuple(out)

    def inspect_named(self, namespace: str):
        """按字符串读取 Namespace 的只读 View（§Web Plan §12.4）；未 seed 返回 None。"""
        ns = StateNamespace(namespace)
        try:
            return self.inspect(ns)
        except KeyError:
            return None

    def memories(self) -> tuple[dict, ...]:
        """Memory 只读列表（§13F.24 / §Web Plan §12.5）。

        经 Specialized Memory Store 的公开读，返回不可变 View（§16C.11），不是 get_all
        内部状态；每一条合并 entry + current version + runtime_state 的可检索元数据。
        """
        out = []
        store = self._runtime.memory_store
        for entry, version in store.iter_current_memories():
            runtime = store.current_runtime_state(entry.memory_id)
            out.append(
                {
                    "memory_id": entry.memory_id,
                    "memory_type": entry.memory_type,
                    "revision": version.revision,
                    "summary_text": version.summary_text,
                    "content": version.content,
                    "confidence": version.confidence,
                    "importance": version.importance,
                    "emotional_salience": version.emotional_salience,
                    "accessibility": runtime.accessibility,
                    "retrieval_count": runtime.retrieval_count,
                    "source_refs": list(version.source_refs),
                    "domain": version.domain,
                    "provenance": version.provenance,
                    "created_tick_id": version.created_tick_id,
                    "created_runtime_time": (
                        version.created_runtime_time.isoformat()
                        if version.created_runtime_time is not None
                        else None
                    ),
                }
            )
        return tuple(out)

    def retrieve(
        self,
        query: str,
        *,
        memory_types: tuple[str, ...] = (),
        memory_count_budget: int = 5,
        min_accessibility: float = 0.0,
    ):
        """Memory Retrieval（§14C）：经 Capability 的受限检索，非 get_all（§13F.24）。"""
        request = MemoryRetrievalRequest(
            query=query,
            memory_types=memory_types,
            memory_count_budget=memory_count_budget,
            min_accessibility=min_accessibility,
        )
        return self._runtime.memory_retrieval.retrieve(request)

    def summary(self) -> LifeSummaryView:
        """只读 Life 概览（§Web Plan §11 LifeSummaryView）：从现有 Public Read View 派生。"""
        identity = self.inspect(StateNamespace.IDENTITY).data
        body = self.inspect(StateNamespace.BODY).data
        emotion = self.inspect(StateNamespace.EMOTION).data
        self_model = self.inspect(StateNamespace.SELF_MODEL).data
        value = self.inspect(StateNamespace.VALUE).data
        relationship = self.inspect(StateNamespace.RELATIONSHIP).data
        drive = self.inspect(StateNamespace.DRIVE).data
        goal = self.inspect(StateNamespace.GOAL).data
        now = self.now()

        development = DevelopmentContextBuilder().build(
            agent_id=self.agent_id,
            birth_time=identity.birth_time,
            runtime_time=now,
            biological_maturity=body.biological_age,
            domain_experience=self._runtime.experience_index.profile(),
        )
        top_values = tuple(
            v.value_type
            for v in sorted(value.commitments, key=lambda c: c.importance, reverse=True)[:5]
        )
        active_roles = tuple(r.label for r in identity.roles if r.status == "active")
        targets = tuple(r.target_id for r in relationship.relationships)
        active_goals = tuple(
            g.description for g in goal.goals if g.status in ("PROPOSED", "ACTIVE", "PAUSED")
        )
        top_drives = tuple(
            d.drive_type
            for d in sorted(drive.active_drives, key=lambda d: d.activation, reverse=True)[:5]
        )
        domain_experience = tuple(d.domain for d in development.domain_experience.domains)
        return LifeSummaryView(
            life_id=self.agent_id,
            primary_name=identity.primary_name,
            runtime_time=now.isoformat(),
            vital_status=body.vital_status,
            chronological_age=development.chronological_age,
            life_stage=development.life_stage,
            mood=MoodSummary(valence=emotion.mood.valence, arousal=emotion.mood.arousal),
            biological_age=body.biological_age,
            homeostasis=HomeostasisSummary(
                energy=body.homeostasis.energy,
                hydration=body.homeostasis.hydration,
                nutrition=body.homeostasis.nutrition,
            ),
            self_esteem=self_model.self_esteem,
            active_roles=active_roles,
            relationship_targets=targets,
            top_values=top_values,
            active_goals=active_goals,
            top_drives=top_drives,
            domain_experience=domain_experience,
        )

    # -- Checkpoint / Branch（§16C.13 / §16C.17） --
    def checkpoint(self) -> Checkpoint:
        cp = self._runtime.checkpoint()
        self._checkpoints.append(cp)
        return cp

    def list_checkpoints(self) -> tuple[Checkpoint, ...]:
        """列出本生命周期内创建的 Checkpoint（进程内跟踪，§Web Plan §14）。"""
        return tuple(self._checkpoints)

    def find_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        for cp in self._checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        raise KeyError(checkpoint_id)

    def branch(
        self, name: str = "branch", *, checkpoint_id: str | None = None
    ) -> "LifeBranchHandle":
        # §12.9 / §14：Checkpoint ≠ Branch；可从指定 Checkpoint Fork，缺省 Fork 当前快照。
        cp = self.find_checkpoint(checkpoint_id) if checkpoint_id is not None else self.checkpoint()
        branch = fork(
            cp,
            registry=self._runtime.registry,
            branch_name=name,
            parent_branch_id=self.branch_id,
            id_gen=self._branch_ids,
        )
        handle = LifeBranchHandle(branch)
        self._branches.append(handle)
        return handle

    def restore_checkpoint(self, checkpoint_id: str) -> "LifeHandle":
        """RESTORE（§16C.14 / §39.10）：以 Checkpoint 快照为种子重建 Runtime 延续原生命。

        忠实调用 Public Restore 语义（等价 `AnimaFlux.restore`）：v0.1 用独立 InMemory 后端
        承载，不覆盖原历史、不修改 current pointer（§21.4）。返回新的 LifeHandle。
        """
        cp = self.find_checkpoint(checkpoint_id)
        runtime = LifeRuntime(
            self.agent_id, InMemoryBackend(), llm=self._runtime.llm, environment=self._runtime.environment
        )
        register_default_life(runtime)
        for ns_value, state in cp.states.items():
            runtime.seed(StateNamespace(ns_value), state)
        return LifeHandle(runtime, agent_id=self.agent_id)

    def list_branches(self):
        """列出从本生命 Fork 出的 Branch 元数据（§Web Plan §33）。"""
        return tuple(b.record for b in self._branches)

    def get_branch(self, branch_id: str) -> "LifeBranchHandle":
        for b in self._branches:
            if b.branch_id == branch_id:
                return b
        raise KeyError(branch_id)

    # -- Timeline / Development / Trace（§Web Plan §10 / §12.6 / §12.7） --
    def timeline(self) -> tuple[ReplayedTick, ...]:
        """只读历史时间线（Commit Journal → ReplayedTick，§21.3）。"""
        return ReplayEngine(self._runtime.backend).replay_timeline(self.agent_id)

    def development(self):
        """从真实历史派生的 Development Context（§24.14），非 Source-of-Truth。

        domain_experience 从 Specialized Memory Store 派生的 Experience Index 取（§7），
        因此 Age ≠ Experience（§24.9）：同龄可不同阅历，同阅历可不同龄。
        """
        identity = self.inspect(StateNamespace.IDENTITY).data
        body = self.inspect(StateNamespace.BODY).data
        roles = tuple(r.label for r in identity.roles if r.status == "active")
        return DevelopmentContextBuilder().build(
            agent_id=self.agent_id,
            birth_time=identity.birth_time,
            runtime_time=self.now(),
            biological_maturity=body.biological_age,
            role_refs=roles,
            domain_experience=self._runtime.experience_index.profile(),
        )

    def now(self) -> datetime:
        return self._runtime.now()


class LifeBranchHandle:
    """Fork 出的分支操作入口（§16C.17）：branch_id 不同，post-fork 独立演化。"""

    def __init__(self, branch: LifeBranch) -> None:
        self._branch = branch
        self.agent_id = branch.checkpoint.agent_id
        self.branch_id = branch.record.branch_id

    def step(self, influences, context=None):
        return self._branch.step(influences, context)

    def read(self, namespace: StateNamespace):
        return self._branch.read(namespace)

    def snapshot(self) -> dict[str, object]:
        """分支当前头的只读状态快照（§Web Plan §33 Branch Compare）。"""
        return {ns.value: self._branch.read(ns) for ns in self._branch.store.committed_namespaces()}

    @property
    def record(self):
        return self._branch.record


def _as_bootstrap(bootstrap: CharacterBootstrap | dict | None) -> CharacterBootstrap:
    if bootstrap is None:
        return CharacterBootstrap()
    if isinstance(bootstrap, CharacterBootstrap):
        return bootstrap
    return CharacterBootstrap(**bootstrap)


def _build_backend(backend_cfg):
    """从配置构造 PersistenceBackend（§16C / Web Plan §6）。

    后端是 Public Facade 的职责，Web 只传配置、不 import SQLite 仓库内部（§Web Plan §2/§10）。
    """
    if backend_cfg is None:
        return None  # 缺省 InMemory
    if isinstance(backend_cfg, str):
        spec = backend_cfg.strip()
        if spec in ("memory", "inmemory"):
            return InMemoryBackend()
        if spec.startswith("sqlite://"):
            return SqliteBackend(spec[len("sqlite://"):])
        if spec.startswith("sqlite:"):
            return SqliteBackend(spec[len("sqlite:"):])
        return SqliteBackend(spec)  # 裸路径视为 SQLite 文件
    if isinstance(backend_cfg, dict):
        kind = backend_cfg.get("type", "sqlite")
        if kind in ("memory", "inmemory"):
            return InMemoryBackend()
        if kind == "sqlite":
            return SqliteBackend(backend_cfg.get("path", "animaflux.db"))
        raise ValueError(f"未知 backend type: {kind}")
    return backend_cfg  # 已是 PersistenceBackend 实例


def _build_llm(llm_cfg: dict) -> LLMCallStrategy:
    """从配置构造 LLM Call Strategy（§15D.1）。v0.1 仅支持 SiliconFlow（OpenAI-compatible）。"""
    provider = llm_cfg.get("provider", "siliconflow")
    if provider == "siliconflow":
        kwargs: dict = {}
        if llm_cfg.get("api_key"):
            kwargs["api_key"] = llm_cfg["api_key"]
        if llm_cfg.get("model"):
            kwargs["model"] = llm_cfg["model"]
        if llm_cfg.get("base_url"):
            kwargs["base_url"] = llm_cfg["base_url"]
        provider_obj = SiliconFlowProvider(**kwargs)
    else:
        raise ValueError(f"未知 LLM provider: {provider}")
    return LLMCallStrategy(provider_obj, model=provider_obj.model)


def _last_tick_number(commits) -> int:
    """从 Commit Journal 恢复 Tick 计数；seed commit 形如 <agent>:C0-*，tick commit 形如 <agent>:C<N>。"""
    tick = 0
    for commit in commits:
        m = re.fullmatch(r".*:C(\d+)", commit.commit_id)
        if m:
            tick = max(tick, int(m.group(1)))
    return tick
