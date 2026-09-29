"""Scenario Environment（v5.9 §12E A4/A5）。

一个具体的外部世界替身：`ScenarioState` 持「外部世界事实」（**不是 Core State**，不进
StateStore，§12E 铁律）。`resolve_action` 把 Action Intent 确定性改造成世界状态并返回
Observation；`poll_observations` 返回排程的外部事件（如「演讲日到了」）。

Environment 绝不直接写 Core State：ActionResult 只携带 Observation，由 LifeRuntime.act()
回灌 `step(observations=...)` → Perception → Appraisal → Influence → Owner（§12E §11）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from animaflux.contracts.environment import (
    ActionIntent,
    ActionResult,
    Observation,
    ObservationBatch,
)
from animaflux.kernel.ids import IdGenerator

# v0.1 动作词汇（§12E §14）：首版只做这三个，外加 rest / wait 作为「什么都不做」的表达。
ACTION_VOCABULARY: frozenset[str] = frozenset(
    {"prepare_task", "seek_feedback", "communicate", "rest", "wait"}
)


@dataclass
class ScenarioState:
    """外部世界事实（§12E §12）。可变、非 Versioned、不进 StateStore。"""

    facts: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.facts[key] = value

    def inc(self, key: str, amount: int = 1) -> int:
        self.facts[key] = self.facts.get(key, 0) + amount
        return self.facts[key]


class ScenarioEnvironment:
    """最小可用的 EnvironmentAdapter：supported_actions + resolve_action（幂等）+ submit + poll。

    具体规则由子类覆写 `_resolve`；`poll_observations` 默认返回空（无排程外部事件）。
    """

    def __init__(self, *, supported: frozenset[str], start_time: datetime | None = None) -> None:
        self.state = ScenarioState()
        self._supported = frozenset(supported)
        self._ids = IdGenerator("ENV", width=None)
        self._resolved: dict[str, ActionResult] = {}
        self.resolve_count = 0

    # -- EnvironmentAdapter --
    def supported_actions(self) -> frozenset[str]:
        return self._supported

    def resolve_action(self, intent: ActionIntent, context: Any = None) -> ActionResult:
        """解析 Action Intent → 改世界状态 + 返回 Observation（§12E §10）。

        按 intent_id 幂等（§22 / §27.5）：同一意图不重复执行。
        """
        existing = self._resolved.get(intent.intent_id)
        if existing is not None:
            return existing
        self.resolve_count += 1
        result = self._resolve(intent, context)
        self._resolved[intent.intent_id] = result
        return result

    def submit_action(self, intent: ActionIntent) -> ActionResult:
        return self.resolve_action(intent)

    def poll_observations(self, world_time: datetime) -> ObservationBatch:
        return ObservationBatch(observations=(), world_time=world_time)

    # -- 钩子 --
    def _resolve(self, intent: ActionIntent, context: Any) -> ActionResult:
        raise NotImplementedError

    # -- 工具 --
    def _result(
        self,
        intent: ActionIntent,
        *,
        status: str,
        consequence: Any = None,
        observation_content: Any = None,
    ) -> ActionResult:
        observations: tuple[Observation, ...] = ()
        if observation_content is not None:
            observations = (
                Observation(
                    observation_id=self._ids.next(),
                    modality="visual",
                    content=observation_content,
                    world_time=intent.world_time,
                    source_entity="scenario",
                    clarity=1.0,
                    intensity=0.6,
                ),
            )
        return ActionResult(
            result_id=self._ids.next(),
            intent_id=intent.intent_id,
            status=status,
            world_time=intent.world_time,
            consequence=consequence,
            observations=observations,
        )


class FirstPresentationScenario(ScenarioEnvironment):
    """多日「首次演讲」场景（§12E §21-22）：世界排期一场演讲，生命在事前主动准备。

    - 主动动作：prepare_task（准备 +1）/ seek_feedback（反馈 +1）/ rest（休息 +1）/ communicate（求助）。
    - 排程外部事件：world_time 到达 `presentation_at` 时，`poll_observations` 按 `preparation`
      解析演讲成败（成功 = gain → joy；失败 = loss → sadness）。
    """

    def __init__(
        self,
        *,
        presentation_at: datetime,
        required_preparation: int = 2,
        start_time: datetime | None = None,
    ) -> None:
        super().__init__(
            supported=ACTION_VOCABULARY,
            start_time=start_time,
        )
        self.presentation_at = presentation_at
        self.required_preparation = required_preparation

    def _resolve(self, intent: ActionIntent, context: Any) -> ActionResult:
        action = intent.action_type
        if action == "prepare_task":
            prep = self.state.inc("preparation")
            return self._result(
                intent,
                status="success",
                consequence={"preparation": prep},
                observation_content="You made steady progress preparing your talk.",
            )
        if action == "seek_feedback":
            feedback = self.state.inc("feedback")
            return self._result(
                intent,
                status="success",
                consequence={"feedback": feedback},
                observation_content="Your mentor pointed out a concrete way to improve.",
            )
        if action == "rest":
            rest = self.state.inc("rest")
            return self._result(
                intent,
                status="success",
                consequence={"rest": rest},
                observation_content="You took a break and recovered some energy.",
            )
        if action == "communicate":
            return self._result(
                intent,
                status="success",
                consequence={"support_seek": True},
                observation_content="You reached out for support and felt a little steadier.",
            )
        if action == "wait":
            return self._result(intent, status="success", consequence={"waited": True})
        return self._result(intent, status="blocked", consequence={"unsupported": action})

    def poll_observations(self, world_time: datetime) -> ObservationBatch:
        """演讲日：按当前准备度解析演讲，返回一个 Observation（成功→gain / 失败→loss）。"""
        if world_time < self.presentation_at:
            return ObservationBatch(observations=(), world_time=world_time)
        if self.state.get("presentation_done"):
            return ObservationBatch(observations=(), world_time=world_time)

        preparation = self.state.get("preparation", 0)
        success = preparation >= self.required_preparation
        self.state.set("presentation_done", True)
        self.state.set("presentation_success", success)

        if success:
            content = "Your first presentation was a success — the room applauded warmly."
        else:
            content = "Your first presentation went badly — you failed to connect with the audience."

        observation = Observation(
            observation_id=self._ids.next(),
            modality="auditory",
            content=content,
            world_time=world_time,
            source_entity="audience",
            clarity=1.0,
            intensity=0.9,
        )
        return ObservationBatch(observations=(observation,), world_time=world_time)
