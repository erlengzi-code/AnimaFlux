"""LifeRuntime — 最小可运行 Life Loop 切片（v5.9 §16C.22 / §16.13 / §19）。

串起一个数字生命的一个 Tick：advance World Time → begin_tick → 注入时间衰减 Influence →
State Resolver 裁决 → Validation → Transaction Coordinator Durable Commit（§16.2 每个成功
Tick 都必须形成 Durable Commit）。本切片只含 Identity / Body / Emotion，Perception / Appraisal
等后续阶段接入。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from animaflux.contracts.appraisal import AppraisableItem
from animaflux.contracts.communication import CommunicativeIntent
from animaflux.contracts.context import ExecutionContext, TimeContext
from animaflux.contracts.decision import DecisionTriggerType
from animaflux.contracts.environment import (
    ActionIntent,
    AgencyDecisionRecord,
    AgencyOutcome,
    EnvironmentAdapter,
    Observation,
    ObservationBatch,
)
from animaflux.contracts.influence import Influence
from animaflux.contracts.memory import MemoryRetrievalRequest
from animaflux.contracts.persistence import StateVersionRecord
from animaflux.contracts.state import StateNamespace
from animaflux.contracts.turn import TurnResult
from animaflux.kernel.ids import IdGenerator
from animaflux.kernel.random import RandomService
from animaflux.kernel.registry import CapabilityRegistry, NamespaceRegistry
from animaflux.kernel.time import Clock
from animaflux.llm.call_strategy import LLMCallRequest, LLMCallStrategy
from animaflux.memory.experience import ExperienceIndex
from animaflux.memory.formation import MemoryFormationProcess
from animaflux.memory.memory_store import MemoryStore
from animaflux.memory.retrieval import MemoryRetrievalCapability
from animaflux.plugins.default_cognition.agency import derive_proactive_candidates
from animaflux.plugins.default_cognition.appraisal import AppraisalProcess, derive_emotion_influences
from animaflux.plugins.default_cognition.communication import CommunicationProcess
from animaflux.plugins.default_cognition.decision import DecisionProcess, make_candidate
from animaflux.plugins.default_cognition.motivation import (
    derive_belief_influences,
    derive_drive_influences,
    derive_goal_review_influences,
    derive_relationship_influences,
)
from animaflux.plugins.default_cognition.perception import PerceptionProcess
from animaflux.plugins.default_cognition.reflection import EvidenceItem, ReflectionProcess
from animaflux.plugins.default_cognition.slow_development import (
    derive_slow_influences,
    evidence_item_for_appraisal,
)
from animaflux.plugins.default_life.body import INFLUENCE_TIME_UPDATE as BODY_TIME_UPDATE
from animaflux.plugins.default_life.drive import INFLUENCE_DECAY as DRIVE_DECAY
from animaflux.plugins.default_life.emotion import INFLUENCE_DECAY as EMOTION_DECAY
from animaflux.plugins.default_life.relationship import INFLUENCE_DECAY as RELATIONSHIP_DECAY
from animaflux.runtime.checkpoint import Checkpoint, capture_checkpoint
from animaflux.runtime.context import RuntimeContextImpl
from animaflux.runtime.resolver import StateResolver
from animaflux.runtime.transaction import TickCommitError, TransactionCoordinator
from animaflux.state.state_store import StateStore

# LLM language-realization 的薄系统提示（§15D.13）：只做「表达」，不做决策，不新增事实。
_REALIZE_SYSTEM_PROMPT = (
    "You are the language realization module of an agent. Given a decided communicative "
    "intent (speech act, disclosure policy, content intents), produce ONE short natural "
    "utterance in the same language as the content intents. Strictly obey the disclosure "
    "policy: never mention forbidden claims, never add facts not present in the content "
    "intents, and do not answer questions. Output only the utterance text, no quotes, no "
    "explanation."
)

# Appraisal Tag → (speech_act, content)。Decision 的确定性候选来源（§14D.43 policy）。
_TAG_TO_RESPONSE: dict[str, tuple[str, str]] = {
    "threat": ("WARN", "there may be danger ahead."),
    "gain": ("THANK", "that's very kind of you."),
    "loss": ("COMFORT", "I'm sorry you're going through this."),
    "opportunity": ("INFORM", "that sounds like a good opportunity."),
}
_DEFAULT_RESPONSE: tuple[str, str] = ("INFORM", "I understand.")

# Reflection（§14F.12 Scheduler 管理频率）：累计证据达到该阈值才反思，避免每 Tick 反思。
REFLECTION_EVIDENCE_THRESHOLD = 3
# 只有整体显著度达到该值的 Appraisal 才进入反思证据缓冲（§14F.3 只反思「值得反思」的经历）。
REFLECTION_EVIDENCE_SIGNIFICANCE = 0.3
# Diary（Narrative 的对外呈现，§13M）：显著度达该值的经历自动写日记（确定性触发；LLM 只做文风）。
AUTO_DIARY_SIGNIFICANCE = 0.5
# 日记正文的 LLM 薄系统提示：只做第一人称表达，不新增事实、不编造（§15D.13）。
_DIARY_SYSTEM_PROMPT = (
    "You are the diary-writing module of an agent. Given facts about what the agent just "
    "experienced (an event, recalled memories, current emotion, world facts, an optional topic), "
    "write ONE short first-person diary entry in the same language as the facts. Write only "
    "about what is given; never invent events, people, or details. Distinguish what the agent "
    "remembers, feels, and decides. Output only the diary text — no title, no quotes, no "
    "explanation."
)


def _perceived_text(content: Any) -> str:
    """感知内容的轻量文本化，仅用于 Retrieval Query 构造（§14C.2 结构化请求）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return f"{content.get('type', '')} {content.get('text', '')}"
    return str(content)


def _version_id(agent_id: str, namespace: str, revision: int) -> str:
    """Durable State Version ID（§16B.1）：agent_id + namespace + revision 全局唯一。

    同一 SQLite 后端承载多条生命（state_version.state_version_id 是全局主键），版本 ID 必须
    带 agent 命名空间，否则第二条生命的 `identity_v1` 会与第一条冲突（UNIQUE 约束）。
    """
    return f"{agent_id}:{namespace}_v{revision}"


class LifeRuntime:
    """一个数字生命的最小 Runtime：Identity + Body + Emotion + 时间推进 + Durable Commit。"""

    def __init__(
        self,
        agent_id: str,
        backend,
        *,
        start_time: datetime | None = None,
        llm: LLMCallStrategy | None = None,
        environment: EnvironmentAdapter | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.backend = backend
        self.llm = llm
        self.environment = environment  # §12E：Life ↔ World 双向循环的环境插头（可选）
        self.registry = NamespaceRegistry()
        self.store = StateStore(agent_id, registry=self.registry)
        self.resolver = StateResolver(self.store, self.registry)
        self.coordinator = TransactionCoordinator(backend)
        self.clock = Clock(start=start_time)
        self.random = RandomService(root_seed=0)
        self.capabilities = CapabilityRegistry()
        self._owners: dict[StateNamespace, object] = {}
        self._serialize: dict[StateNamespace, object] = {}
        self._validate_fn: dict[StateNamespace, object] = {}
        self._influence_ids = IdGenerator("INF", width=None)
        self._tick = 0
        self.perception = PerceptionProcess()
        self.appraisal = AppraisalProcess()
        self.communication = CommunicationProcess()
        self.decision = DecisionProcess()
        # Memory 子系统（P7）：Specialized Store 是 Source of Truth（§13F.9），
        # Experience Index 是 Derived / 可重建（§7）；Retrieval 经 Capability 受限访问（§13F.24）。
        self.memory_store = MemoryStore(agent_id)
        self.experience_index = ExperienceIndex()
        self.memory_retrieval = MemoryRetrievalCapability(self.memory_store)
        self.memory_formation = MemoryFormationProcess()
        # P9：Slow Self Development —— Reflection（低频）把显著经历沉淀成慢状态 Influence（§14F）。
        self.reflection = ReflectionProcess()
        self._evidence_buffer: list[EvidenceItem] = []
        # Diary（§13M）：待写日记的显著经历（内容 + 标签），由 _auto_diary 在 Tick 内消费。
        self._diary_pending: dict | None = None
        # §12E：主动决策的「为什么」叙事（运行时内存，不入 Commit Journal / Checkpoint）。
        self._agency_log: list[AgencyDecisionRecord] = []

    # -- 装配 --
    def register_owner(self, namespace: StateNamespace, owner, *, serialize, validate=None) -> None:
        self.registry.register_owner(namespace, owner)
        self._owners[namespace] = owner
        self._serialize[namespace] = serialize
        self._validate_fn[namespace] = validate

    def seed(self, namespace: StateNamespace, state) -> None:
        """初始化一个 State 的 v1，并 Durable Commit（§16.2 Agent 创建即持久化）。"""
        self.store.seed(namespace, state)
        state_version_id = _version_id(self.agent_id, namespace.value, 1)
        rec = StateVersionRecord(
            state_version_id=state_version_id,
            agent_id=self.agent_id,
            namespace=namespace.value,
            revision=1,
            payload=self._serialize[namespace](state),
        )
        self.coordinator.commit_tick(
            agent_id=self.agent_id,
            tick_id="t0",
            commit_id=f"{self.agent_id}:C0-{namespace.value}",
            new_versions=[rec],
            version_map={namespace.value: state_version_id},
        )

    def load_committed(self, namespace: StateNamespace, version: int, state) -> None:
        """RESTORE：从持久化后端恢复已提交状态，不重新 Durable Commit（§21.1）。"""
        self.store.restore_committed(namespace, version, state)

    def resume_tick(self, tick_count: int) -> None:
        """RESTORE 时恢复 Tick 计数器，避免 commit_id/tick_id 与既有 Journal 冲突（§21.1）。"""
        self._tick = tick_count

    # -- 生命周期 --
    def step(
        self,
        delta_seconds: float,
        *,
        extra_influences: tuple[Influence, ...] = (),
        observations: tuple[Observation, ...] = (),
    ) -> str:
        world_time = self.clock.advance(timedelta(seconds=delta_seconds))
        self._tick += 1
        tick_id = f"t{self._tick}"
        self.store.begin_tick()
        context = self._context(world_time, tick_id, delta_seconds)
        influences = self._time_influences(delta_seconds, world_time) + list(extra_influences)
        influences.extend(self._cognition_influences(observations, world_time, context))
        # §Life Loop 第 11 步：Reflection & Slow-State Update（§14F.12 低频，阈值内不触发）
        influences.extend(self._run_reflection(world_time))
        # §Life Loop 第 12 步：Diary（§13M）——显著经历自动落一篇第一人称日记（确定性触发）。
        influences.extend(self._auto_diary(world_time))
        outcome = self.resolver.resolve(influences, context)
        if not outcome.ok:
            self.store.rollback()
            raise RuntimeError(f"tick '{tick_id}' failed: {outcome.error}")

        # 校验 + Durable Commit（§16.2 / §19.7）
        new_versions: list[StateVersionRecord] = []
        version_map: dict[str, str] = {}
        for ns in outcome.changed_namespaces:
            state = self.store.read(ns)
            validate = self._validate_fn.get(ns)
            if validate is not None:
                validate(state)
            new_v = self.store.read_version(ns)
            old_v = self.store.committed_version(ns)
            state_version_id = _version_id(self.agent_id, ns.value, new_v.version)
            rec = StateVersionRecord(
                state_version_id=state_version_id,
                agent_id=self.agent_id,
                namespace=ns.value,
                revision=new_v.version,
                payload=self._serialize[ns](state),
                parent_version_id=_version_id(self.agent_id, ns.value, old_v.version),
                created_tick_id=tick_id,
            )
            new_versions.append(rec)
            version_map[ns.value] = state_version_id

        try:
            self.coordinator.commit_tick(
                agent_id=self.agent_id,
                tick_id=tick_id,
                commit_id=f"{self.agent_id}:C{self._tick}",
                new_versions=new_versions,
                version_map=version_map,
                runtime_time_after=world_time.isoformat(),
            )
        except TickCommitError:
            self.store.rollback()
            raise
        self.store.commit()
        return tick_id

    def read(self, namespace: StateNamespace):
        return self.store.read(namespace)

    def now(self) -> datetime:
        return self.clock.now()

    def checkpoint(self) -> Checkpoint:
        """快照当前 Committed 版本地图 + 不可变状态，作为 Restore / Branch 的 Fork 点（§21.6）。"""
        version_map: dict[str, str] = {}
        states: dict[str, object] = {}
        for ns in self.store.committed_namespaces():
            version = self.store.committed_version(ns)
            version_map[ns.value] = _version_id(self.agent_id, ns.value, version.version)
            states[ns.value] = version.state
        return capture_checkpoint(
            agent_id=self.agent_id,
            world_time=self.now(),
            version_map=version_map,
            states=states,
            fingerprint={"root_seed": self.random.root_seed},
        )

    def send_text(self, text: str, *, delta_seconds: float = 1.0) -> TurnResult:
        """Human 对话 Convenience API（§16C.8）。

        完整 Cognition：HumanInteraction → Observation → Perception → Appraisal → Emotion
        Influence → Resolver → Commit，再经确定性 Communication 产出回应。绝不等于
        llm.chat()（§16C.8 / §16C.12）。
        """
        world_time = self.now()
        obs = Observation(
            observation_id=self._influence_ids.next(),
            modality="communication",
            content=text,
            world_time=world_time,
            clarity=1.0,
            intensity=0.7,
            source_entity="human",
        )
        context = self._context(world_time, "send_text", delta_seconds)
        perceived, results = self._perceive_appraise((obs,), world_time, context)
        influences = list(
            derive_emotion_influences(results, world_time=world_time, id_gen=self._influence_ids)
        )
        influences.extend(self._motivation_influences(results, perceived, world_time))
        tick_id = self.step(delta_seconds, extra_influences=tuple(influences))
        # Memory Formation 位于该次交互的 Durable Commit 之后，用真实 tick_id / 推进后的时间。
        self._form_memories(perceived, results, runtime_time=self.now(), tick_id=tick_id)
        utterance = self._respond(results)
        return TurnResult(
            text=utterance,
            tick_id=tick_id,
            runtime_time=self.now().isoformat(),
            committed=True,
            trace_ref=perceived.perceived_events[0].perceived_event_id if perceived.perceived_events else None,
        )

    def act(self, *, delta_seconds: float = 0.0) -> AgencyOutcome:
        """一次「主动决策机会」（§12E）：无外部 Observation 触发，由内部动机（Goal / Need）驱动。

        第二条合法决策入口（§12E）：Internal Motivation → Decision → ActionIntent → Environment
        → ActionResult → Observation → Perception。Environment 绝不直接写 Core State：结果只经
        Observation 回灌 `step()`（§12E §11）。不调 LLM（Deterministic First §15D.2）。
        """
        if self.environment is None:
            raise RuntimeError(
                "proactive action requires an environment; pass environment=... to AnimaFlux"
            )

        world_time = self.now()
        goal_state = self._read_optional(StateNamespace.GOAL)
        drive_state = self._read_optional(StateNamespace.DRIVE)
        belief_state = self._read_optional(StateNamespace.BELIEF)
        world_model_state = self._read_optional(StateNamespace.WORLD_MODEL)

        goal_refs = self._active_goal_ids()
        urgency = self._drive_urgency()
        motivation_refs = tuple(
            getattr(n, "need_id", "")
            for n in getattr(drive_state, "needs", ()) or ()
            if float(getattr(n, "intensity", 0.0) or 0.0) > 0.0
        )

        frame = self.decision.frame(
            "what to do next, proactively",
            trigger_refs=tuple(goal_refs),
            trigger_type=DecisionTriggerType.INTERNAL.value,
            goal_refs=goal_refs,
            urgency=urgency,
            time_horizon="near_term",
        )
        candidates = derive_proactive_candidates(
            goal_state=goal_state,
            drive_state=drive_state,
            belief_state=belief_state,
            world_model_state=world_model_state,
            supported_actions=self.environment.supported_actions(),
            id_gen=self._influence_ids,
        )
        result = self.decision.decide(frame, candidates)

        if result.selected_candidate_ref is None:
            no_action_reason = result.no_action_reason
            if not candidates:
                no_action_reason = "no proactive candidate (no active goal / need / information gap)"
            record = AgencyDecisionRecord(
                decision_id=result.decision_id,
                world_time=world_time,
                trigger_type=DecisionTriggerType.INTERNAL.value,
                relevant_goal_refs=goal_refs,
                motivation_refs=motivation_refs,
                confidence=result.confidence,
                no_action_reason=no_action_reason,
            )
            self._agency_log.append(record)
            return AgencyOutcome(acted=False, decision=result)

        selected = next(c for c in candidates if c.candidate_id == result.selected_candidate_ref)
        intent = ActionIntent(
            intent_id=self._influence_ids.next(),
            actor=self.agent_id,
            action_type=selected.action_type,
            world_time=world_time,
            content=selected.description,
            motivation_refs=motivation_refs,
            initiative="proactive",
            goal_refs=goal_refs,
            expected_outcome=selected.description,
        )
        action_result = self.environment.resolve_action(intent)
        # 回灌：ActionResult.observations → Perception → Appraisal → Influence → Owner（§12E §11）
        tick_id = None
        if action_result.observations:
            tick_id = self.step(delta_seconds, observations=action_result.observations)

        record = AgencyDecisionRecord(
            decision_id=result.decision_id,
            world_time=world_time,
            trigger_type=DecisionTriggerType.INTERNAL.value,
            relevant_goal_refs=goal_refs,
            motivation_refs=motivation_refs,
            selected_action_type=selected.action_type,
            initiative="proactive",
            expected_outcome=selected.description,
            confidence=result.confidence,
        )
        self._agency_log.append(record)
        return AgencyOutcome(
            acted=True,
            decision=result,
            intent=intent,
            action_result=action_result,
            tick_id=tick_id,
        )

    def agency_log(self) -> tuple[AgencyDecisionRecord, ...]:
        """主动决策的「为什么」叙事（§12E A8），运行时内存，只读。"""
        return tuple(self._agency_log)

    def _respond(self, results) -> str:
        """回应（§16C.8 / §14D → §14E）：Decision 四阶段产出 CommunicativeIntent，再经 Communication 转成表达。

        确定性优先（§15D.2 / §14D.43）：Framing / Candidate / Evaluation / Selection 由代码决定；
        LLM 只做 language realization（§15D.3），且仅在配置了 Provider 且意图适用时启用；任何失败
        或未配置都回退到确定性模板（§15D.23 / §14E.31.6）。
        """
        tags = tuple(tag for r in results for tag in r.tags)
        # 阶段一：Framing（§14D.5）——当前到底在决定什么：如何回应这次交流。
        frame = self.decision.frame(
            "how to respond to the human",
            trigger_refs=tuple(ref for r in results for ref in r.source_refs),
            goal_refs=self._active_goal_ids(),
            urgency=self._drive_urgency(),
        )
        # 阶段二：Candidate Generation（§14D.6）——由 Appraisal Tag 映射到确定性候选（§14D.43 policy）。
        speech_act, content = _DEFAULT_RESPONSE
        for tag in ("threat", "gain", "loss", "opportunity"):
            if tag in tags:
                speech_act, content = _TAG_TO_RESPONSE[tag]
                break
        candidate = make_candidate(
            self._influence_ids.next(),
            f"communicate:{speech_act}",
            description=content,
            source="policy",
            feasibility=1.0,
        )
        # 阶段三 + 四：Evaluation + Selection（§14D.9 / §14D.11 Satisficing）。
        result = self.decision.decide(frame, [candidate])
        if result.selected_candidate_ref is None:
            # 无可接受候选（§14D.11）→ 保守 no-op 回应（§14E.31.6）
            speech_act, content = "INFORM", "I understand."
        intent = CommunicativeIntent(
            intent_ref=self._influence_ids.next(),
            actor_ref=self.agent_id,
            target_refs=("human",),
            speech_act=speech_act,
            content_intents=(content,),
            disclosure_policy="fully_disclose",
            source_refs=tuple(ref for r in results for ref in r.source_refs),
            decision_ref=result.decision_id,
        )
        draft = self._llm_realize(intent) if self._llm_applicable(intent) else None
        return self.communication.realize(intent, draft_text=draft).utterance

    def _llm_applicable(self, intent: CommunicativeIntent) -> bool:
        """确定性 LLMNeedAssessment（§15D.4 的 v0.1 最小版）。

        只有「完全/部分披露」的自然语言表达才交给 LLM；withhold / redirect / vague 等
        隐瞒类意图一律走确定性保守模板（§14E.5），不允许 LLM 自行改写。
        """
        if self.llm is None:
            return False
        if intent.disclosure_policy not in ("fully_disclose", "partially_disclose"):
            return False
        return bool(intent.content_intents)

    def _llm_realize(self, intent: CommunicativeIntent) -> str | None:
        """LLM 只负责把既定 Intent 变成自然语句（language realization），不决定内容边界。"""
        user_msg = json.dumps(
            {
                "speech_act": intent.speech_act,
                "disclosure_policy": intent.disclosure_policy,
                "content_intents": list(intent.content_intents),
                "allowed_claims": list(intent.allowed_claims),
                "forbidden_claims": list(intent.forbidden_claims),
            },
            ensure_ascii=False,
        )
        request = LLMCallRequest(
            logical_call_id=f"realize:{intent.intent_ref}",
            process_id="communication",
            prompt_template_id="communication.realize",
            prompt_version="v1",
            input={
                "messages": [
                    {"role": "system", "content": _REALIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 128,
                "temperature": 0.7,
            },
        )
        try:
            record = self.llm.call(request)
            text = str((record.result or {}).get("text", "")).strip()
            return text or None
        except Exception:
            # Provider 失败 → 确定性 fallback（§15D.23），不阻塞生命 Tick
            return None

    # -- 内部 --
    def _time_influences(self, delta_seconds: float, world_time: datetime) -> list[Influence]:
        """每个 Tick 由 Runtime 注入的时间衰减（§13B / §13D / §13E.9 / §13J.19）。"""
        influences = []
        seeded = self._seeded()
        if StateNamespace.BODY in seeded:
            influences.append(
                self._influence(
                    StateNamespace.BODY, BODY_TIME_UPDATE, 0.0,
                    {"delta_seconds": delta_seconds}, world_time,
                )
            )
        if StateNamespace.EMOTION in seeded:
            influences.append(
                self._influence(
                    StateNamespace.EMOTION, EMOTION_DECAY, 0.0,
                    {"delta_seconds": delta_seconds}, world_time,
                )
            )
        if StateNamespace.DRIVE in seeded:
            influences.append(
                self._influence(
                    StateNamespace.DRIVE, DRIVE_DECAY, 0.0,
                    {"delta_seconds": delta_seconds}, world_time,
                )
            )
        if StateNamespace.RELATIONSHIP in seeded:
            influences.append(
                self._influence(
                    StateNamespace.RELATIONSHIP, RELATIONSHIP_DECAY, 0.0,
                    {"delta_seconds": delta_seconds}, world_time,
                )
            )
        return influences

    def _seeded(self) -> set[StateNamespace]:
        """已持久化（t0 seed / 已 commit）的 Namespace 集合（§16.2）。"""
        return set(self.store.committed_namespaces())

    def _read_optional(self, namespace: StateNamespace):
        """读一个可能尚未 seed 的 State；未 seed 返回 None（供主动候选派生用）。"""
        try:
            return self.store.read(namespace)
        except KeyError:
            return None

    def _relationship_targets(self) -> set[str]:
        try:
            rel = self.store.read(StateNamespace.RELATIONSHIP)
        except KeyError:
            return set()
        return {r.target_id for r in rel.relationships}

    def _goal_descriptions(self) -> set[str]:
        try:
            goal = self.store.read(StateNamespace.GOAL)
        except KeyError:
            return set()
        return {g.description for g in goal.goals}

    def _active_goal_ids(self) -> tuple[str, ...]:
        try:
            goal = self.store.read(StateNamespace.GOAL)
        except KeyError:
            return ()
        return tuple(g.goal_id for g in goal.goals if g.status in ("PROPOSED", "ACTIVE", "PAUSED"))

    def _drive_urgency(self) -> float:
        try:
            drive = self.store.read(StateNamespace.DRIVE)
        except KeyError:
            return 0.0
        return max((d.urgency for d in drive.active_drives), default=0.0)

    def _retrieve_for(self, perceived):
        """Retrieval（§14C）：用当前感知内容做 cued retrieval，作为 Appraisal 的 familiarity 信号。"""
        if not perceived or not perceived.perceived_events:
            return None
        query = " ".join(_perceived_text(pe.perceived_content) for pe in perceived.perceived_events)
        return self.memory_retrieval.retrieve(
            MemoryRetrievalRequest(query=query, memory_count_budget=5, mode="cued")
        )

    def _motivation_influences(
        self,
        results,
        perceived,
        world_time: datetime,
    ) -> list[Influence]:
        """Appraisal → Drive / Belief / Relationship / Goal 的 Influence（§13E/§13G/§13I/§13J）。

        只在对应 State 已 seed 时派生（§16.2）；否则该维度尚未进入生命切片，不产生空转 Influence。
        """
        if not results or perceived is None:
            return []
        seeded = self._seeded()
        influences: list[Influence] = []
        if StateNamespace.DRIVE in seeded:
            influences.extend(derive_drive_influences(results, world_time=world_time, id_gen=self._influence_ids))
        perceived_by_ref = {pe.perceived_event_id: pe for pe in perceived.perceived_events}
        if StateNamespace.BELIEF in seeded:
            influences.extend(
                derive_belief_influences(results, perceived_by_ref, world_time=world_time, id_gen=self._influence_ids)
            )
        if StateNamespace.RELATIONSHIP in seeded:
            influences.extend(
                derive_relationship_influences(
                    results, perceived_by_ref,
                    existing_targets=self._relationship_targets(),
                    world_time=world_time, id_gen=self._influence_ids,
                )
            )
        if StateNamespace.GOAL in seeded:
            influences.extend(
                derive_goal_review_influences(
                    results,
                    existing_goal_descriptions=self._goal_descriptions(),
                    world_time=world_time, id_gen=self._influence_ids,
                )
            )
        return influences

    def _accumulate_reflection_evidence(self, perceived, results) -> None:
        """把显著 Appraisal 累积成反思证据（§14F.3/§14F.5），供低频 Reflection 使用。"""
        if not perceived or not results:
            return
        perceived_by_ref = {pe.perceived_event_id: pe for pe in perceived.perceived_events}
        for r in results:
            if r.overall_significance < REFLECTION_EVIDENCE_SIGNIFICANCE:
                continue
            pe = perceived_by_ref.get(r.appraisable_item_ref)
            item = evidence_item_for_appraisal(r, pe)
            if item is not None:
                self._evidence_buffer.append(item)

    def _value_ids_by_type(self) -> dict[str, str]:
        """Value type → value_id 映射，供 Reflection 慢更新定位既有 Value Commitment（§13H）。"""
        try:
            value = self.store.read(StateNamespace.VALUE)
        except KeyError:
            return {}
        return {v.value_type: v.value_id for v in value.commitments}

    def _run_reflection(self, world_time: datetime, *, force: bool = False) -> list[Influence]:
        """低频 Reflection（§14F.12）：累计证据达阈值（或显式 force）时反思成慢状态 Influence。"""
        if not self._evidence_buffer:
            return []
        if not force and len(self._evidence_buffer) < REFLECTION_EVIDENCE_THRESHOLD:
            return []
        result = self.reflection.reflect(self.agent_id, tuple(self._evidence_buffer))
        self._evidence_buffer.clear()
        return list(
            derive_slow_influences(
                result,
                value_by_type=self._value_ids_by_type(),
                world_time=world_time,
                id_gen=self._influence_ids,
            )
        )

    def reflect_now(self) -> str:
        """显式触发 Reflection（§14F.1 Trigger）：把累计证据反思成慢状态 Influence 并 Durable Commit。"""
        world_time = self.now()
        influences = self._run_reflection(world_time, force=True)
        return self.step(0.0, extra_influences=tuple(influences))

    # -- Diary（§13M）：Narrative 的对外呈现。写不写 / 写什么事实 / 落库由代码确定性负责，LLM 只做文风。 --
    def diary_entries(self) -> tuple[dict, ...]:
        """读当前 NarrativeState.chapters，串行化为日记条目（新在前）。§13M.1 是重构而非流水账。"""
        try:
            narrative = self.store.read(StateNamespace.NARRATIVE)
        except KeyError:
            return ()
        entries = []
        for c in narrative.chapters:
            entries.append({
                "chapter_id": c.chapter_id,
                "title": c.title,
                "time": c.start_time.isoformat() if c.start_time else None,
                "summary": c.summary,
                "memory_refs": list(c.memory_refs),
            })
        return tuple(reversed(entries))

    def write_diary(self, *, topic: str | None = None, time_start=None, time_end=None) -> dict:
        """点击写日记：按话题 / 时间段取上下文 → 合成散文 → narrative.add_chapter → Durable Commit。"""
        if StateNamespace.NARRATIVE not in self._seeded():
            raise RuntimeError("narrative state is not seeded; cannot write diary")
        facts = self._diary_context(topic=topic, time_start=time_start, time_end=time_end)
        entry_id = self._influence_ids.next()
        summary = self._synthesize_diary(facts, entry_id)
        title = self._diary_title(summary)
        refs = tuple(facts.get("memory_refs") or ())
        influence = self._diary_influence(entry_id, title, summary, self.now(), refs)
        self.step(0.0, extra_influences=(influence,))
        return {
            "chapter_id": entry_id,
            "title": title,
            "time": self.now().isoformat(),
            "summary": summary,
            "memory_refs": list(refs),
            "committed": True,
        }

    def _maybe_set_diary_pending(self, perceived, results) -> None:
        """显著 Appraisal（§13M.2 值得叙事的经历）→ 置待写日记；由 _auto_diary 在 Tick 内消费。"""
        if not perceived or not results:
            return
        best = max(results, key=lambda r: r.overall_significance)
        if best.overall_significance < AUTO_DIARY_SIGNIFICANCE:
            return
        perceived_by_ref = {pe.perceived_event_id: pe for pe in perceived.perceived_events}
        pe = perceived_by_ref.get(best.appraisable_item_ref)
        event_text = _perceived_text(pe.perceived_content) if pe is not None else ""
        refs = tuple(pe.source_event_refs) if pe is not None else ()
        if not refs and pe is not None:
            refs = (pe.perceived_event_id,)
        self._diary_pending = {"event": event_text, "memory_refs": refs}

    def _auto_diary(self, world_time: datetime) -> list[Influence]:
        """每 Tick 至多一篇：待写日记存在时合成散文并落 narrative.add_chapter（确定性触发）。"""
        if self._diary_pending is None:
            return []
        pending = self._diary_pending
        self._diary_pending = None
        if StateNamespace.NARRATIVE not in self._seeded():
            return []
        facts = self._diary_context(event=pending.get("event"))
        entry_id = self._influence_ids.next()
        summary = self._synthesize_diary(facts, entry_id)
        title = self._diary_title(summary)
        refs = tuple(dict.fromkeys(tuple(pending.get("memory_refs") or ()) + tuple(facts.get("memory_refs") or ())))
        return [self._diary_influence(entry_id, title, summary, world_time, refs)]

    def _diary_context(self, *, topic=None, time_start=None, time_end=None, event=None) -> dict:
        """收集日记所需的全部事实（事件 / 记忆 / 情绪 / 自我 / 世界），只收不造。"""
        query = topic or event or None
        pairs = self._memory_summaries(query=query, time_start=time_start, time_end=time_end, limit=6)
        return {
            "event": event,
            "topic": topic,
            "memories": [text for text, _ in pairs],
            "memory_refs": [ref for _, ref in pairs],
            "emotion": self._emotion_text(),
            "self": self._self_text(),
            "world": self._world_facts_text(),
        }

    def _memory_summaries(self, *, query=None, time_start=None, time_end=None, limit=6) -> list[tuple[str, str]]:
        """取 (summary, memory_id)。有 query 走 cued retrieval；否则按时间段过滤当前记忆（新在前）。"""
        if query:
            retrieved = self.memory_retrieval.retrieve(
                MemoryRetrievalRequest(query=query, memory_count_budget=limit)
            )
            return [(m.summary_text or _perceived_text(m.content), m.memory_id) for m in retrieved.memories]
        out = []
        for entry, version in reversed(self.memory_store.iter_current_memories()):
            ts = version.created_runtime_time
            if time_start is not None and ts is not None and ts < time_start:
                continue
            if time_end is not None and ts is not None and ts > time_end:
                continue
            out.append((version.summary_text or _perceived_text(version.content), entry.memory_id))
            if len(out) >= limit:
                break
        return out

    def _emotion_text(self) -> str | None:
        try:
            emo = self.store.read(StateNamespace.EMOTION)
        except KeyError:
            return None
        active = [e for e in emo.episodes if e.status == "active"]
        if not active:
            return "calm"
        return ", ".join(sorted({e.emotion_type for e in active}))

    def _self_text(self) -> str | None:
        try:
            sm = self.store.read(StateNamespace.SELF_MODEL)
        except KeyError:
            return None
        bits = [f"self-esteem {sm.self_esteem:.2f}"]
        for a in sorted(sm.self_efficacy, key=lambda a: a.assessment, reverse=True)[:2]:
            bits.append(f"capable in {a.domain} ({a.assessment:.2f})")
        return "; ".join(bits)

    def _world_facts_text(self) -> list[str]:
        try:
            wm = self.store.read(StateNamespace.WORLD_MODEL)
        except KeyError:
            return []
        facts = []
        for e in wm.entities:
            facts.append(e.label or e.entity_ref)
        for r in wm.relations:
            facts.append(f"{r.from_ref} {r.relation_type} {r.to_ref}")
        for c in wm.causal_rules:
            facts.append(c.statement)
        return facts

    def _synthesize_diary(self, facts: dict, entry_id: str) -> str:
        """LLM 只做文风（language realization）；失败 / 无 key → 确定性回退模板（§15D.23）。"""
        if self.llm is not None:
            text = self._diary_realize(facts, entry_id)
            if text:
                return text
        return self._diary_fallback(facts)

    def _diary_realize(self, facts: dict, entry_id: str) -> str | None:
        user_msg = json.dumps(facts, ensure_ascii=False)
        request = LLMCallRequest(
            logical_call_id=f"diary:{entry_id}",
            process_id="diary",
            prompt_template_id="diary.entry",
            prompt_version="v1",
            input={
                "messages": [
                    {"role": "system", "content": _DIARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 256,
                "temperature": 0.8,
            },
        )
        try:
            record = self.llm.call(request)
            text = str((record.result or {}).get("text", "")).strip()
            return text or None
        except Exception:
            # Provider 失败 → 确定性 fallback（§15D.23），不阻塞生命 Tick
            return None

    def _diary_fallback(self, facts: dict) -> str:
        """确定性第一人称回退：只用已收集的事实拼接，绝不编造（§15D.23）。"""
        parts = []
        if facts.get("event"):
            parts.append(f"I experienced: {facts['event']}.")
        if facts.get("topic"):
            parts.append(f"I'm thinking about: {facts['topic']}.")
        memories = facts.get("memories") or []
        if memories:
            parts.append("I remember: " + "; ".join(memories) + ".")
        emotion = facts.get("emotion")
        if emotion:
            parts.append(f"I feel {emotion}.")
        self_text = facts.get("self")
        if self_text:
            parts.append(f"Right now, {self_text}.")
        world = facts.get("world") or []
        if world:
            parts.append("What I know: " + "; ".join(world) + ".")
        if not parts:
            parts.append("Another day passed.")
        return " ".join(parts)

    def _diary_title(self, text: str) -> str:
        first = (text or "").strip().replace("\n", " ").strip()
        if not first:
            return "—"
        for sep in (". ", "。", "! ", "！", "? ", "？", "; ", "；"):
            idx = first.find(sep)
            if 0 < idx <= 24:
                return first[: idx + 1].strip()
        if len(first) > 24:
            return first[:24].rstrip() + "…"
        return first

    def _diary_influence(self, entry_id: str, title: str, summary: str, world_time: datetime, memory_refs) -> Influence:
        refs = tuple(memory_refs or ())
        return Influence(
            influence_id=entry_id,
            source_plugin="runtime.lifeloop",
            target_state=StateNamespace.NARRATIVE.value,
            influence_type="narrative.add_chapter",
            magnitude=1.0,
            created_at=world_time,
            cause_event_refs=refs,
            metadata={
                "title": title,
                "summary": summary,
                "start_time": world_time,
                "memory_refs": list(refs),
            },
        )

    def _cognition_influences(
        self,
        observations: tuple[Observation, ...],
        world_time: datetime,
        context: RuntimeContextImpl,
    ) -> list[Influence]:
        """Perception → Retrieval → Appraisal → Memory Formation → Emotion + Motivation Influence（§15B）。"""
        perceived, results = self._perceive_appraise(observations, world_time, context)
        if not observations:
            return []
        # Memory Formation 位于 Appraisal 之后（§16B.20），形成长期 Memory（§13F.6）。
        self._form_memories(perceived, results, runtime_time=world_time, tick_id=context.execution.tick_id)
        influences = list(
            derive_emotion_influences(results, world_time=world_time, id_gen=self._influence_ids)
        )
        influences.extend(self._motivation_influences(results, perceived, world_time))
        return influences

    def _perceive_appraise(
        self,
        observations: tuple[Observation, ...],
        world_time: datetime,
        context: RuntimeContextImpl,
    ):
        """Perception → Retrieval → Appraisal（§15B.6/§14C/§15B.8），返回 (perceived, results)，无副作用。"""
        if not observations:
            return None, ()
        batch = ObservationBatch(observations=observations, world_time=world_time)
        perceived = self.perception.perceive(
            batch, context, sensory_capabilities=self._body_capabilities()
        )
        retrieved = self._retrieve_for(perceived)
        items = tuple(
            AppraisableItem(
                item_ref=pe.perceived_event_id,
                item_type="perceived_event",
                content=pe.perceived_content,
                salience=pe.salience,
                source_refs=pe.source_event_refs,
            )
            for pe in perceived.perceived_events
        )
        results = self.appraisal.appraise(items, context, retrieved=retrieved)
        return perceived, results

    def _form_memories(self, perceived, results, *, runtime_time: datetime, tick_id: str) -> None:
        """把 Appraisal 之后的显著 PerceivedEvent 写入 Specialized Memory Store（§13F.6/§16B.20）。

        Memory 是 Specialized Store（Source of Truth，§13F.9），写入由其所属模块的 Formation
        Process 完成；同时增量更新 Derived Experience Index（§7）。Forgetting ≠ Delete
        （§13F.15）与 retrieving ≠ rewriting（§16B.15）由 Store 保证。
        """
        if not perceived or not results:
            return
        self._accumulate_reflection_evidence(perceived, results)
        self._maybe_set_diary_pending(perceived, results)
        perceived_by_ref = {pe.perceived_event_id: pe for pe in perceived.perceived_events}
        for candidate in self.memory_formation.propose(results, perceived_by_ref):
            memory_id = self.memory_store.form(
                candidate.memory_type,
                candidate.content,
                summary_text=candidate.summary_text,
                confidence=candidate.confidence,
                importance=candidate.importance,
                emotional_salience=candidate.emotional_salience,
                source_refs=candidate.source_refs,
                provenance=candidate.provenance,
                domain=candidate.domain,
                tick_id=tick_id,
                runtime_time=runtime_time,
            )
            self.experience_index.record(
                self.memory_store.get_entry(memory_id),
                self.memory_store.get_current_version(memory_id),
            )

    def _body_capabilities(self) -> dict[str, float] | None:
        try:
            body = self.store.read(StateNamespace.BODY)
        except KeyError:
            return None
        return asdict(body.capabilities)

    def _influence(
        self,
        namespace: StateNamespace,
        influence_type: str,
        magnitude: float,
        metadata: dict,
        world_time: datetime,
    ) -> Influence:
        return Influence(
            influence_id=self._influence_ids.next(),
            source_plugin="runtime.lifeloop",
            target_state=namespace.value,
            influence_type=influence_type,
            magnitude=magnitude,
            created_at=world_time,
            metadata=metadata,
        )

    def _context(self, world_time: datetime, tick_id: str, delta_seconds: float) -> RuntimeContextImpl:
        return RuntimeContextImpl(
            execution=ExecutionContext(
                runtime_id="runtime",
                agent_id=self.agent_id,
                tick_id=tick_id,
                plugin_id="runtime.lifeloop",
                process_id="loop",
                phase="step",
            ),
            time=TimeContext(world_time=world_time, delta_time=timedelta(seconds=delta_seconds)),
            random=self.random,
            capabilities=self.capabilities,
        )
