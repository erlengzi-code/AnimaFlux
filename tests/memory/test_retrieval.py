"""P7 Memory Retrieval 测试（§14C：预算化 / 类型过滤 / 排名 / Stored≠Retrievable / read-only）。"""

from animaflux.contracts.memory import MemoryRetrievalRequest
from animaflux.memory.memory_store import MemoryStore
from animaflux.memory.retrieval import MemoryRetrievalCapability


def _store():
    store = MemoryStore("agent-1")
    store.form("episodic", "我在河边钓鱼", importance=0.9, source_refs=("EVT-1",))
    store.form("semantic", "钓鱼需要耐心和工具", importance=0.5)
    store.form("episodic", "我吃过一次火锅", importance=0.3)
    return store


def test_budget_limits_result_count():
    cap = MemoryRetrievalCapability(_store())
    result = cap.retrieve(MemoryRetrievalRequest(query="钓鱼", memory_count_budget=1))
    assert result.budget_used == 1
    assert len(result.memories) == 1
    # 高重要度 + 语义命中优先
    assert result.memories[0].content == "我在河边钓鱼"


def test_memory_type_filter():
    cap = MemoryRetrievalCapability(_store())
    result = cap.retrieve(MemoryRetrievalRequest(query="", memory_types=("semantic",)))
    assert all(m.memory_type == "semantic" for m in result.memories)


def test_stored_not_retrievable_when_accessibility_low():
    store = MemoryStore("agent-1")
    mid = store.form("episodic", "我见过老王")
    store.decay_accessibility(mid, factor=0.01)
    cap = MemoryRetrievalCapability(store)
    result = cap.retrieve(MemoryRetrievalRequest(query="老王", min_accessibility=0.1))
    assert result.memories == ()  # Stored ≠ Retrievable（§14C.5）
    assert result.status == "NOT_FOUND"


def test_not_found_is_valid_result():
    # 无候选（空 Store）→ NOT_FOUND 是合法认知结果（§14C.17），不是异常
    cap = MemoryRetrievalCapability(MemoryStore("agent-empty"))
    result = cap.retrieve(MemoryRetrievalRequest(query="任意主题"))
    assert result.status == "NOT_FOUND"
    assert result.memories == ()


def test_retrieve_is_read_only():
    store = _store()
    cap = MemoryRetrievalCapability(store)
    before = store.get_current_version("MEM-1")
    cap.retrieve(MemoryRetrievalRequest(query="钓鱼"))
    after = store.get_current_version("MEM-1")
    assert after is before  # 检索不改内容（§14C.13）
