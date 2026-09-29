"""⑩ 日记系统（§13M）：Narrative 的对外呈现。

自动写（确定性显著度门槛，LLM 只做文风）＋ 点击写（话题 / 时间段）。日记 = NarrativeState
.chapters 里的 LifeChapter，复用 frozen Narrative，零新增 State / Process。正文以真实 LLM 散文
为主，无 key / 失败回退确定性第一人称模板（§15D.23）。只走公开 API + scripted-fake LLM。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.environment import Observation
from animaflux.contracts.state import StateNamespace


def test_write_diary_falls_back_deterministically_without_llm():
    """无 LLM：写日记回退确定性第一人称模板，仍落库 committed（§15D.23）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-diary-write")
    assert handle.diary() == ()

    result = handle.write_diary(topic="my first day")

    assert result["committed"] is True
    assert result["chapter_id"]
    assert result["title"]
    assert "my first day" in result["summary"]

    entries = handle.diary()
    assert len(entries) == 1
    assert entries[0]["summary"] == result["summary"]

    # 复用 frozen Narrative：恰好一条 chapter（Copy-on-Write，不覆盖旧版本）
    narrative = handle.inspect(StateNamespace.NARRATIVE).data
    assert len(narrative.chapters) == 1
    assert narrative.chapters[0].summary == result["summary"]

    # 再写一篇：追加新 chapter，不删除/覆盖旧一篇（Narrative 是版本化叙事）
    result2 = handle.write_diary(topic="later in the day")
    assert result2["chapter_id"] != result["chapter_id"]
    assert len(handle.diary()) == 2


def test_write_diary_uses_scripted_llm_prose(scripted_llm):
    """配置 scripted-fake LLM：正文用 scripted 散文，但「写不写/写什么事实/落库」仍由代码负责。"""
    llm, provider = scripted_llm("I recall my first day vividly.")
    flux = AnimaFlux(llm=llm)
    handle = flux.create_life("func-diary-llm")

    result = handle.write_diary(topic="my first day")

    assert provider.calls == 1
    assert result["summary"] == "I recall my first day vividly."
    assert result["committed"] is True
    assert handle.diary()[0]["summary"] == "I recall my first day vividly."


def test_significant_event_auto_writes_diary():
    """显著经历（significance ≥ 0.5）自动写日记：Observation → step → narrative.add_chapter（同 Tick）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-diary-auto")
    assert handle.diary() == ()

    handle.observe(
        Observation(
            observation_id="obs-danger",
            modality="observation",
            content="there is danger nearby",
            world_time=handle.now(),
            clarity=1.0,
            intensity=1.0,
            source_entity="human",
        )
    )

    entries = handle.diary()
    assert len(entries) == 1
    assert "danger" in entries[0]["summary"].lower()
    # 自动日记带 provenance（触发它的感知事件 ref），可追溯（§13M.12）
    assert entries[0]["memory_refs"]


def test_insignificant_event_does_not_auto_write():
    """低显著经历（significance < 0.5）不触发自动日记（确定性门槛，不靠 LLM 判断）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-diary-quiet")

    handle.observe(
        Observation(
            observation_id="obs-breeze",
            modality="observation",
            content="a quiet breeze",
            world_time=handle.now(),
            clarity=1.0,
            intensity=0.3,
            source_entity="human",
        )
    )

    assert handle.diary() == ()
