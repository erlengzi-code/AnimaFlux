"""P7 Experience Index 测试（Cross-cutting：Domain-specific / Derived / Rebuildable）。"""

from datetime import datetime

from animaflux.memory.experience import ExperienceIndex
from animaflux.memory.memory_store import MemoryStore


def test_experience_is_domain_specific_not_global():
    store = MemoryStore("agent-1")
    store.form("episodic", "处理一次冲突", domain="social.conflict", importance=0.8, runtime_time=datetime(2000, 1, 1))
    store.form("procedural", "公开演讲技巧", domain="skill.public_speaking", importance=0.6, runtime_time=datetime(2000, 1, 2))

    idx = ExperienceIndex()
    idx.rebuild(store.iter_current_memories())

    conflict = idx.domain("social.conflict")
    speaking = idx.domain("skill.public_speaking")
    assert conflict is not None and speaking is not None
    assert conflict.exposure == 1
    assert speaking.exposure == 1
    # procedural 记忆进入 procedural_refs
    assert speaking.procedural_refs != ()


def test_experience_index_rebuildable_from_source():
    store = MemoryStore("agent-1")
    store.form("episodic", "第一次冲突", domain="social.conflict", importance=0.9, runtime_time=datetime(2000, 1, 1))
    store.form("episodic", "第二次冲突", domain="social.conflict", importance=0.4, runtime_time=datetime(2000, 1, 3))

    incremental = ExperienceIndex()
    for entry, version in store.iter_current_memories():
        incremental.record(entry, version)

    rebuilt = ExperienceIndex()
    rebuilt.rebuild(store.iter_current_memories())

    assert incremental.profile() == rebuilt.profile()  # 派生索引可从 Source 重建


def test_significant_episodes_tracked_by_importance():
    store = MemoryStore("agent-1")
    store.form("episodic", "重大冲突", domain="social.conflict", importance=0.9)
    store.form("episodic", "日常小摩擦", domain="social.conflict", importance=0.3)

    idx = ExperienceIndex()
    idx.rebuild(store.iter_current_memories())

    conflict = idx.domain("social.conflict")
    assert conflict.exposure == 2
    assert len(conflict.significant_episode_refs) == 1  # 只有高重要度进入
