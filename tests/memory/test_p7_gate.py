"""P7 ★Gate 必需测试（§Roadmap / §24.9 / §6）：

- Same Age, Different Experience（同龄不同阅历）
- Different Age, Same Relevant Experience（不同龄同相关阅历）
- Experience ≠ Competence ≠ Self-Efficacy（阅历 ≠ 能力 ≠ 自我效能）

走 Public Facade（AnimaFlux.create_life + LifeHandle.observe + development()）验证完整
接线：Perception → Appraisal → Memory Formation → Specialized Store → Experience Index →
DevelopmentContext。Age 由 Identity.birth_time + Runtime Time 派生；Experience 由真实记忆
历史派生；两者正交（§24.9）。
"""

from __future__ import annotations

from datetime import datetime

from animaflux.api import AnimaFlux
from animaflux.contracts.environment import Observation
from animaflux.memory.experience import ExperienceIndex
from animaflux.memory.memory_store import MemoryStore

BIRTH = datetime(1980, 1, 1)
START = datetime(2000, 1, 1)  # 出生 20 年后的启动时刻


def _domain_obs(text: str, domain: str, *, intensity: float = 0.8) -> Observation:
    """带 Domain 标签 + 显式 novelty 的 Observation，走完整认知后应形成 Domain Memory。"""
    return Observation(
        observation_id=f"OBS-{text}",
        modality="observation",
        content={"text": text, "domain": domain, "novelty": 0.4},
        world_time=START,
        clarity=1.0,
        noise=0.0,
        intensity=intensity,
        source_entity="human",
    )


def _experience(handle, domain: str):
    return handle.development().domain_experience.domain(domain)


def test_same_age_different_experience():
    """同龄（同 birth_time / 同 start_time）但不同领域阅历 → age 相同、experience 不同。"""
    a = AnimaFlux().create_life("life-a", bootstrap={"birth_time": BIRTH}, start_time=START)
    b = AnimaFlux().create_life("life-b", bootstrap={"birth_time": BIRTH}, start_time=START)

    for text in ("冲突一", "冲突二", "冲突三"):
        a.observe(_domain_obs(text, "social.conflict"))

    dev_a = a.development()
    dev_b = b.development()

    # Same Age：life_stage 相同，chronological_age 差在秒级（observe 各推进 1s）
    assert dev_a.life_stage == dev_b.life_stage
    assert abs((dev_a.chronological_age - dev_b.chronological_age).total_seconds()) < 60

    # Different Experience：A 有 social.conflict 阅历，B 没有
    assert _experience(a, "social.conflict").exposure == 3
    assert _experience(b, "social.conflict") is None


def test_different_age_same_relevant_experience():
    """不同龄但同相关领域阅历 → age 不同、该领域 experience 相同。"""
    elder = AnimaFlux().create_life(
        "life-elder", bootstrap={"birth_time": datetime(1960, 1, 1)}, start_time=START  # 40 岁
    )
    younger = AnimaFlux().create_life(
        "life-younger", bootstrap={"birth_time": datetime(1980, 1, 1)}, start_time=START  # 20 岁
    )

    for handle in (elder, younger):
        for text in ("冲突一", "冲突二"):
            handle.observe(_domain_obs(text, "social.conflict"))

    dev_elder = elder.development()
    dev_younger = younger.development()

    # Different Age
    assert dev_elder.life_stage == "adulthood"
    assert dev_younger.life_stage == "adulthood"  # 都成年但年龄不同
    assert dev_elder.chronological_age.days > dev_younger.chronological_age.days

    # Same Relevant Experience：同领域阅历相同
    assert _experience(elder, "social.conflict").exposure == 2
    assert _experience(younger, "social.conflict").exposure == 2


def test_experience_is_not_competence_nor_self_efficacy():
    """高 exposure 不自动带来 competence（success/failure）或 self-efficacy（confidence）。

    §6：Experience ≠ Competence ≠ Self-Efficacy。mere 经历只累积 exposure；能力（成败）与
    自我效能（自信）是独立维度，不因「经历得多」自动提升。
    """
    store = MemoryStore("agent-1")
    for i in range(8):
        # 重要性 < 0.7：不算 significant episode，也不产生任何 success/failure/confidence 变化
        store.form(
            "episodic",
            f"第 {i} 次公开演讲",
            domain="skill.public_speaking",
            importance=0.5,
            runtime_time=START,
        )
    idx = ExperienceIndex()
    idx.rebuild(store.iter_current_memories())

    speaking = idx.domain("skill.public_speaking")
    assert speaking is not None
    assert speaking.exposure == 8  # 阅历累积
    assert speaking.success_count == 0  # 但能力（成败）未被经历自动赋予
    assert speaking.failure_count == 0
    assert speaking.confidence == 0.5  # 自我效能（自信）也未因 exposure 自动改变
    assert speaking.significant_episode_refs == ()  # 低重要度经历不构成 significant episode
