"""Memory 契约（v5.9 §13F / §14C / §16B.12–16B.15）。

Memory = Agent 主观持久记录，不是 Objective Event Log（§13F.1）；Memory ≠ Belief（§13F.2）；
Memory ≠ Narrative（§13F.3）。Event ≠ Perception ≠ Memory（§13F.28.2）。

Specialized Memory Store 三分离（§16B.12）：memory_entry（哪一条逻辑 Memory）/ memory_version
（现在如何记得）/ memory_runtime_state（机械检索元数据）。Reconsolidation 出新版本不覆盖（§16B.14）；
Forgetting ≈ Accessibility Decay，不是 Delete（§13F.15）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    """v0.1 四种 Memory 类型（§13F.4）。"""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    AUTOBIOGRAPHICAL = "autobiographical"


@dataclass(frozen=True)
class MemoryEntry:
    """这是哪一条逻辑 Memory（§16B.13）。"""

    memory_id: str
    agent_id: str
    memory_type: str
    created_tick_id: str | None = None
    status: str = "active"  # active | ...
    created_branch_id: str | None = None
    current_version_id: str | None = None


@dataclass(frozen=True)
class MemoryVersion:
    """现在如何记得这件事（§16B.14）。Reconsolidation 创建新 Version，不覆盖旧 Content。"""

    memory_version_id: str
    memory_id: str
    revision: int
    content: Any
    summary_text: str | None = None
    confidence: float = 0.5
    importance: float = 0.5
    emotional_salience: float = 0.0
    source_refs: tuple[str, ...] = ()
    provenance: str | None = None
    domain: str | None = None  # Domain Experience 标签（Cross-cutting §4），非 §16B.14 强制字段
    created_tick_id: str | None = None
    created_runtime_time: datetime | None = None
    parent_version_id: str | None = None


@dataclass(frozen=True)
class MemoryRuntimeState:
    """机械检索元数据，与 Memory Content Revision 分离（§16B.15）。retrieving ≠ rewriting。"""

    memory_id: str
    accessibility: float = 1.0
    last_retrieved_runtime_time: datetime | None = None
    retrieval_count: int = 0
    updated_tick_id: str | None = None


@dataclass(frozen=True)
class MemoryRetrievalRequest:
    """结构化 Retrieval Request（§14C.2），不是单一字符串 Query。"""

    query: str = ""
    memory_types: tuple[str, ...] = ()
    entity_refs: tuple[str, ...] = ()
    time_start: datetime | None = None
    time_end: datetime | None = None
    memory_count_budget: int = 5
    token_budget: int | None = None
    mode: str = "cued"  # cued | deliberate（§14C.3）
    min_accessibility: float = 0.0  # 低于此 accessibility 的 Memory 当前检索不到（§14C.5 Stored ≠ Retrievable）


@dataclass(frozen=True)
class RetrievedMemory:
    """RetrievedMemorySet 中的一条（§14C.11）。"""

    memory_id: str
    memory_type: str
    revision: int
    content: Any
    summary_text: str | None = None
    confidence: float = 0.5
    importance: float = 0.5
    emotional_salience: float = 0.0
    accessibility: float = 1.0
    retrieval_score: float = 0.0
    source_refs: tuple[str, ...] = ()
    provenance: str | None = None


@dataclass(frozen=True)
class RetrievedMemorySet:
    """结构化 Cognitive Artifact（§14C.11）。「想不起来」是合法认知结果（§14C.17）。"""

    memories: tuple[RetrievedMemory, ...]
    status: str = "FOUND"  # FOUND | PARTIAL | NOT_FOUND | UNCERTAIN
    budget_used: int = 0
    trace: dict[str, Any] = field(default_factory=dict)
