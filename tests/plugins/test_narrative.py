"""P9 Narrative Owner 测试（§13M：Provenance / Versioning / 结构化）。"""

from datetime import datetime

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.narrative import (
    INFLUENCE_ADD_THEME,
    INFLUENCE_ADD_TURNING_POINT,
    INFLUENCE_REVISE,
    LifeChapter,
    NarrativeOwner,
    NarrativeState,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None, iid: str = "INF-1") -> Influence:
    return Influence(
        influence_id=iid, source_plugin="test", target_state="narrative",
        influence_type=influence_type, magnitude=0.0, created_at=T0,
        metadata=metadata or {},
    )


def test_turning_point_requires_provenance():
    # Turning Point 必须可回溯到具体事件（§13M.12）
    owner = NarrativeOwner()
    out = owner.resolve(NarrativeState(), [
        _inf(INFLUENCE_ADD_TURNING_POINT, {"description": "决定离开家乡", "importance": 0.9}),
    ], None).next_state
    assert len(out.turning_points) == 0  # 无 source_refs → 不落（§13M.12）


def test_theme_requires_provenance():
    owner = NarrativeOwner()
    out = owner.resolve(NarrativeState(), [
        _inf(INFLUENCE_ADD_THEME, {"name": "独立自主"}),
    ], None).next_state
    assert len(out.themes) == 0


def test_turning_point_with_source_refs_stored():
    owner = NarrativeOwner()
    out = owner.resolve(NarrativeState(), [
        _inf(INFLUENCE_ADD_TURNING_POINT, {"description": "决定离开家乡", "source_refs": ("EV-1",)}, "TP-1"),
    ], None).next_state
    assert len(out.turning_points) == 1
    assert out.turning_points[0].source_refs == ("EV-1",)


def test_revise_bumps_version_and_keeps_history():
    owner = NarrativeOwner()
    state = NarrativeState()
    revised = owner.resolve(state, [
        _inf(INFLUENCE_REVISE, {"note": "重述童年章节"}),
    ], None).next_state
    assert revised.revision == 2  # 版本化（§13M.14）
    assert revised.history == ("r1: 重述童年章节",)


def test_narrative_is_structured_not_memory_copy():
    # Narrative 是重构，结构化为章节/主题/转折点，引用 memory_refs 而非复制事件（§13M.2 / §13M.3）
    chapter = LifeChapter(chapter_id="C-1", title="求学时代", memory_refs=("M-1", "M-2"))
    assert chapter.memory_refs == ("M-1", "M-2")  # 引用而非内容
    assert not hasattr(chapter, "event_content")
    state = NarrativeState()
    assert hasattr(state, "themes")
    assert hasattr(state, "turning_points")
    assert hasattr(state, "chapters")
