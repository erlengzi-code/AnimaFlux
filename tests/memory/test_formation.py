"""P7 Memory Formation 测试（§13F.6：不是所有 Event 都形成记忆；persist / ignore）。

不变式：Memory content 取 Perceived Content（主观记录），Event ≠ Perception ≠ Memory
（§13F.28.2）；importance / emotional_salience / confidence 各司其职（§13F.7）。
"""

from datetime import datetime

from animaflux.contracts.appraisal import AppraisalResult
from animaflux.contracts.perception import PerceivedEvent
from animaflux.memory.formation import MemoryFormationProcess

T0 = datetime(2000, 1, 1)


def _pe(ref="PE-1", content="外面下雨了", modality="observation", confidence=0.9, salience=0.8):
    return PerceivedEvent(
        perceived_event_id=ref,
        modality=modality,
        perceived_content=content,
        confidence=confidence,
        clarity=1.0,
        salience=salience,
        uncertainty=0.1,
        noticed_at=T0,
        source_observation_refs=("OBS-1",),
        source_event_refs=("EVT-1",),
    )


def _result(ref="PE-1", significance=0.6, tags=("threat",), source_refs=("EVT-1",)):
    return AppraisalResult(
        appraisal_id="APR-1",
        appraisable_item_ref=ref,
        relevance=0.6,
        overall_significance=significance,
        tags=tags,
        source_refs=source_refs,
    )


def test_significant_event_forms_candidate():
    proc = MemoryFormationProcess()
    cands = proc.propose((_result(significance=0.6),), {"PE-1": _pe()})
    assert len(cands) == 1
    c = cands[0]
    assert c.content == "外面下雨了"  # 主观 Perceived Content，非 Objective Event（§13F.28.2）
    assert c.importance == 0.6  # importance 取 Appraisal significance
    assert c.emotional_salience == 0.7  # threat → 情绪显著度
    assert c.confidence == 0.9  # confidence 取 Perception confidence
    assert c.memory_type == "episodic"
    assert c.source_refs == ("EVT-1", "OBS-1")


def test_insignificant_event_is_ignored():
    proc = MemoryFormationProcess()
    cands = proc.propose((_result(significance=0.05),), {"PE-1": _pe()})
    assert cands == ()  # §13F.6 不是所有 Event 都形成长期 Memory


def test_no_emotion_tags_gives_zero_salience():
    proc = MemoryFormationProcess()
    cands = proc.propose((_result(tags=()),), {"PE-1": _pe()})
    assert len(cands) == 1
    assert cands[0].emotional_salience == 0.0


def test_domain_and_memory_type_hints_carried():
    proc = MemoryFormationProcess()
    content = {"text": "处理一次冲突", "domain": "social.conflict", "memory_type": "episodic"}
    cands = proc.propose((_result(significance=0.5),), {"PE-1": _pe(content=content)})
    assert len(cands) == 1
    assert cands[0].domain == "social.conflict"
    assert cands[0].memory_type == "episodic"


def test_unmatched_result_is_skipped():
    proc = MemoryFormationProcess()
    # AppraisalResult 引用了不存在的 PerceivedEvent ref → 跳过，不抛异常
    assert proc.propose((_result(ref="MISSING"),), {"PE-1": _pe()}) == ()
