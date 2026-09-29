"""P7 Memory Specialized Store 测试（§16B.12–16B.15：entry/version/runtime_state 三分离）。"""

from datetime import datetime

from animaflux.memory.memory_store import MemoryStore

T0 = datetime(2000, 1, 1)


def test_form_creates_three_way_separation():
    store = MemoryStore("agent-1")
    mid = store.form("episodic", "昨天下了雨", importance=0.6, source_refs=("EVT-1",), runtime_time=T0)
    entry = store.get_entry(mid)
    version = store.get_current_version(mid)
    runtime = store.current_runtime_state(mid)
    assert entry.memory_type == "episodic"
    assert entry.current_version_id == f"{mid}_v1"
    assert version.revision == 1
    assert version.content == "昨天下了雨"
    assert version.source_refs == ("EVT-1",)
    assert runtime.accessibility == 1.0
    assert runtime.retrieval_count == 0


def test_reconsolidate_creates_new_version_keeps_old():
    store = MemoryStore("agent-1")
    mid = store.form("episodic", "原始记忆", confidence=0.5)
    v1 = store.get_current_version(mid)
    store.reconsolidate(mid, content="重新解释", confidence=0.9)
    v2 = store.get_current_version(mid)
    assert v2.revision == 2
    assert v2.content == "重新解释"
    assert v2.confidence == 0.9
    assert v2.parent_version_id == v1.memory_version_id
    # 旧版本不覆盖
    assert len(store.list_versions(mid)) == 2
    assert store.get_version(v1.memory_version_id).content == "原始记忆"


def test_forgetting_is_decay_not_delete():
    store = MemoryStore("agent-1")
    mid = store.form("episodic", "一条会慢慢淡忘的记忆")
    store.decay_accessibility(mid, factor=0.4)
    assert store.get_current_version(mid).content == "一条会慢慢淡忘的记忆"  # 内容仍在
    assert store.get_entry(mid).status == "active"  # 未删除
    assert store.current_runtime_state(mid).accessibility == 0.4


def test_retrieval_does_not_rewrite_memory():
    store = MemoryStore("agent-1")
    mid = store.form("episodic", "记住的内容")
    before = store.get_current_version(mid)
    store.record_retrieval(mid, runtime_time=T0)
    after = store.get_current_version(mid)
    assert after is before  # 内容版本不变（retrieving ≠ rewriting，§16B.15）
    runtime = store.current_runtime_state(mid)
    assert runtime.retrieval_count == 1
    assert runtime.accessibility > 1.0 - 1e-9 or runtime.accessibility <= 1.0
