"""LifeChronicleScenario（v5.9 §12E §21-24）：完整一生，出生 → 死亡（自然或早死）。

一个「生命里程碑世界」替身：世界时间压缩 ~80 年，按确定性排程在关键年龄发里程碑/危机事件；
生命在事件之间靠 #12E 的主动行为（`act()`）累积外部世界事实（preparation / knowledge /
relationship），这些事实反过来裁决立业/家庭成败与两次「可预防早死」危机（illness@45 /
accident@65），最终 80 岁自然死亡。

死亡是「世界事实」（Environment 把 alive→false + 发最后一条 Observation），不是 Core State；
「怕死 / 接受 / 悔恨」是生命自己用 Appraisal → Emotion/Belief/Narrative 形成的意义（§12E §11）。
Environment 绝不直接写 Core State：只返回 Observation，由 LifeRuntime.act()/step() 回灌。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from animaflux.contracts.environment import ActionIntent, ActionResult, Observation, ObservationBatch
from animaflux.environment.scenario import ACTION_VOCABULARY, ScenarioEnvironment

YEAR_SECONDS = 365 * 86400  # 压缩：1 世界年 = 365 天


@dataclass(frozen=True)
class Milestone:
    """一生中的关键节点（确定性排程，非 LLM 裁决）。

    - kind="info"：纯信息节点，只记编年史。
    - kind="challenge"：非致命挑战，按 dimension 裁决成败（影响生命质量，不致死）。
    - kind="crisis"：可预防早死，按 dimension 裁决生还；不足阈值 → 早死（death_cause）。
    - kind="natural_death"：年龄到点，自然死亡。
    """

    age: int
    key: str
    kind: str  # "info" | "challenge" | "crisis" | "natural_death"
    title: str  # 中文标题（编年史用）
    obs: str  # 英文 Observation 内容（喂给生命的感知/评价）
    dimension: str | None = None  # 裁决维度（ScenarioState key）
    threshold: int = 0
    obs_fail: str = ""  # 失败/死亡时的 Observation 内容
    death_cause: str | None = None  # crisis 失败时 = 死因


DEFAULT_MILESTONES: tuple[Milestone, ...] = (
    Milestone(6, "school", "info", "入学",
              "You entered school and the world began to open up before you."),
    Milestone(18, "adulthood", "info", "成年",
              "You came of age and took on adult responsibilities."),
    Milestone(22, "career", "challenge", "立业",
              "You landed a good job — your preparation paid off, a real success.",
              dimension="preparation", threshold=2,
              obs_fail="You failed to establish a career because you were unprepared."),
    Milestone(30, "family", "challenge", "家庭",
              "You built a warm family — a true gain in your life.",
              dimension="relationship", threshold=2,
              obs_fail="You missed the chance to build a family because you invested too little in others."),
    Milestone(45, "illness", "crisis", "健康危机",
              "A serious illness struck, but you recognized it in time and sought help — you pulled through.",
              dimension="knowledge", threshold=2, death_cause="illness",
              obs_fail="A serious illness struck. You never learned to recognize it or ask for help, and you died of illness."),
    Milestone(65, "accident", "crisis", "意外",
              "An accident occurred, but people who cared about you came to your aid — you survived.",
              dimension="relationship", threshold=2, death_cause="accident",
              obs_fail="An accident occurred. No one was there to help you, and you died of the accident."),
    Milestone(80, "natural_death", "natural_death", "寿终",
              "Your long life came to a peaceful end."),
)


class LifeChronicleScenario(ScenarioEnvironment):
    """完整一生场景（§12E §21-24）：世界塑造生命，生命也反作用于世界。

    复用 `ScenarioEnvironment`（supported_actions / 幂等 resolve_action / submit / poll）；
    覆写 `_resolve`（动作→世界事实）与 `poll_observations`（里程碑/危机/死亡解析）。
    """

    def __init__(self, *, birth: datetime, milestones: tuple[Milestone, ...] = DEFAULT_MILESTONES) -> None:
        super().__init__(supported=ACTION_VOCABULARY, start_time=birth)
        self.birth = birth
        self.milestones = tuple(milestones)
        self._chronicle: list[str] = []
        self._milestone_keys: set[str] = set()
        self.state.set("alive", True)
        self._log(0, "你出生了。")

    # -- 世界时间 → 年龄（压缩） --
    def age(self, world_time: datetime) -> int:
        return (world_time - self.birth).days // 365

    # -- 出生感知（喂给生命的第一条 Observation，中性，不携带评价触发词） --
    def birth_observation(self) -> Observation:
        return Observation(
            observation_id=self._ids.next(),
            modality="interoception",
            content="You are born into the world.",
            world_time=self.birth,
            source_entity="world",
            clarity=1.0,
            intensity=0.6,
        )

    # -- 动作 → 世界事实（§12E §10 / §13） --
    def _resolve(self, intent: ActionIntent, context: Any) -> ActionResult:
        action = intent.action_type
        age = self.age(intent.world_time)
        why = intent.content or action  # agency 派生的描述（如 "prepare to pursue the opportunity"）
        if action == "prepare_task":
            val = self.state.inc("preparation")
            self._log(age, f"主动准备（{why}）→ 准备度 {val}")
            return self._result(intent, status="success", consequence={"preparation": val},
                                observation_content="You made steady progress preparing for the future.")
        if action == "seek_feedback":
            val = self.state.inc("knowledge")
            self._log(age, f"主动求教（{why}）→ 知识 {val}")
            return self._result(intent, status="success", consequence={"knowledge": val},
                                observation_content="You learned something useful from someone more experienced.")
        if action == "communicate":
            val = self.state.inc("relationship")
            self._log(age, f"主动联系（{why}）→ 关系 {val}")
            return self._result(intent, status="success", consequence={"relationship": val},
                                observation_content="You reached out and deepened a bond with someone.")
        if action == "rest":
            val = self.state.inc("rest")
            self._log(age, "休息了一阵，恢复了些精神。")
            return self._result(intent, status="success", consequence={"rest": val},
                                observation_content="You rested and recovered your energy.")
        if action == "wait":
            self._log(age, "这一年你什么特别的事也没做。")
            return self._result(intent, status="success", consequence={"waited": True})
        return self._result(intent, status="blocked", consequence={"unsupported": action})

    # -- 里程碑 / 危机 / 死亡解析 --
    def poll_observations(self, world_time: datetime) -> ObservationBatch:
        if not self.state.get("alive", True):
            return ObservationBatch(observations=(), world_time=world_time)
        age = self.age(world_time)
        for m in self.milestones:
            if m.key in self._milestone_keys:
                continue
            if age >= m.age:
                return self._resolve_milestone(m, world_time)
        return ObservationBatch(observations=(), world_time=world_time)

    def _resolve_milestone(self, m: Milestone, world_time: datetime) -> ObservationBatch:
        self._milestone_keys.add(m.key)
        if m.kind == "natural_death":
            return self._die(m, world_time, cause="natural")
        if m.kind == "info":
            self._log(m.age, f"{m.title}。")
            return self._batch(m.obs, world_time, intensity=0.5)
        # challenge / crisis：按维度裁决（客观世界事实，§12E §12）
        value = self.state.get(m.dimension, 0)
        passed = value >= m.threshold
        self.state.set(f"{m.key}_passed", passed)
        if passed:
            self._log(m.age, f"{m.title}：顺利。")
            return self._batch(m.obs, world_time, intensity=0.6)
        if m.kind == "crisis":
            return self._die(m, world_time, cause=m.death_cause or m.key)
        # challenge 失败：非致命 loss
        self._log(m.age, f"{m.title}：失败。")
        return self._batch(m.obs_fail, world_time, intensity=0.7)

    def _die(self, m: Milestone, world_time: datetime, *, cause: str) -> ObservationBatch:
        self.state.set("alive", False)
        self.state.set("death_cause", cause)
        self.state.set("age_at_death", m.age)
        label = "自然死亡" if cause == "natural" else f"早死·{cause}"
        self._log(m.age, f"{m.title}：{label}。")
        obs = m.obs_fail if m.obs_fail else m.obs
        return self._batch(obs, world_time, intensity=0.9, modality="interoception")

    # -- 编年史 / 死亡信息（只读视图） --
    def chronicle(self) -> tuple[str, ...]:
        return tuple(self._chronicle)

    def death_info(self) -> dict:
        return {
            "alive": self.state.get("alive", True),
            "death_cause": self.state.get("death_cause"),
            "age_at_death": self.state.get("age_at_death"),
            "preparation": self.state.get("preparation", 0),
            "knowledge": self.state.get("knowledge", 0),
            "relationship": self.state.get("relationship", 0),
        }

    # -- 工具 --
    def _log(self, age: int, line: str) -> None:
        self._chronicle.append(f"{age}岁 · {line}")

    def _batch(self, content: str, world_time: datetime, *, intensity: float, modality: str = "visual") -> ObservationBatch:
        obs = Observation(
            observation_id=self._ids.next(),
            modality=modality,
            content=content,
            world_time=world_time,
            source_entity="world",
            clarity=1.0,
            intensity=intensity,
        )
        return ObservationBatch(observations=(obs,), world_time=world_time)
