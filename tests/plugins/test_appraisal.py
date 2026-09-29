"""P6 Appraisal 测试（§14B：多维 / Relevance Screening / 不直接写 State / 转 Emotion Influence）。"""

from datetime import datetime

from animaflux.contracts.appraisal import AppraisableItem
from animaflux.contracts.state import StateNamespace
from animaflux.plugins.default_cognition.appraisal import AppraisalProcess, derive_emotion_influences

T0 = datetime(2000, 1, 1)


def _item(content, salience=0.7, ref="it-1", source_refs=("EVT-1",)):
    return AppraisableItem(item_ref=ref, item_type="perceived_event", content=content, salience=salience, source_refs=source_refs)


def test_detect_threat_tag():
    (r,) = AppraisalProcess().appraise((_item("there is a threat coming"),))
    assert "threat" in r.tags


def test_multiple_tags_coexist_mixed_meaning():
    (r,) = AppraisalProcess().appraise((_item("you face danger but also get a great opportunity"),))
    assert "threat" in r.tags and "opportunity" in r.tags


def test_low_relevance_minimal_appraisal_no_tags():
    (r,) = AppraisalProcess().appraise((_item("a threat", salience=0.01),))
    assert r.tags == ()
    assert r.overall_significance < 0.05


def test_derive_emotion_influence_threat_to_fear():
    results = AppraisalProcess().appraise((_item("danger ahead", salience=0.8),))
    infs = derive_emotion_influences(results, world_time=T0)
    assert len(infs) == 1
    inf = infs[0]
    assert inf.target_state == StateNamespace.EMOTION.value
    assert inf.influence_type == "emotion.trigger"
    assert inf.metadata["emotion_type"] == "fear"
    assert inf.metadata["valence"] < 0.0
    assert inf.magnitude > 0.0
    assert inf.cause_event_refs == ("EVT-1",)


def test_appraisal_outputs_artifact_not_state_mutation():
    # §14B.9：Appraisal 只产出 AppraisalResult；情绪影响由 derive_emotion_influences 单独转换
    results = AppraisalProcess().appraise((_item("gain reward", salience=0.6),))
    (r,) = results
    assert r.goal_impacts == ()  # P6 尚无 Goal State，Facet 留空（§14B.4）
    assert "gain" in r.tags
    infs = derive_emotion_influences(results, world_time=T0)
    assert all(i.influence_type == "emotion.trigger" for i in infs)
