"""P1 Core Contracts 契约测试。

验证 contracts/ 层的类型形状与不变式：
- Event / Influence 创建后不可修改（frozen，§5.16 / §6.16）
- 默认值语义（§5.16 / §6.18）
- StateNamespace 恰好 13 个 Core State（§2）
- ProcessResult / StateResolutionResult 默认值（§12.7 / §7.15）
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from animaflux.contracts import (
    Event,
    ExecutionContext,
    Influence,
    ProcessResult,
    StateNamespace,
    StateResolutionResult,
    TimeContext,
)


def _t() -> datetime:
    return datetime(2024, 1, 1, 9, 0, 0)


def test_event_is_frozen_and_defaults():
    evt = Event(
        event_id="EVT-1",
        event_type="conversation.message.spoken",
        world_time=_t(),
    )
    assert evt.participants == ()
    assert evt.targets == ()
    assert evt.payload == {}
    assert evt.visibility == "public"
    assert evt.causal_refs == ()
    assert evt.importance_hint == 0.0
    assert evt.source is None
    with pytest.raises(FrozenInstanceError):
        evt.event_type = "changed"  # type: ignore[misc]


def test_influence_is_frozen_and_single_target():
    inf = Influence(
        influence_id="INF-1",
        source_plugin="appraisal.default",
        target_state="emotion",
        influence_type="social_rejection",
        magnitude=0.8,
        created_at=_t(),
    )
    assert inf.confidence == 1.0
    assert inf.duration_seconds is None
    assert inf.decay is None
    assert inf.cause_event_refs == ()
    assert inf.cause_memory_refs == ()
    # 一条 Influence 只指向一个 target_state（§6.5）：结构上无多目标字段
    with pytest.raises(FrozenInstanceError):
        inf.target_state = "drive"  # type: ignore[misc]


def test_state_namespace_has_exactly_13_core_states():
    assert len(StateNamespace) == 13
    assert StateNamespace.EMOTION.value == "emotion"
    assert StateNamespace.SELF_MODEL.value == "self_model"


def test_state_resolution_result_defaults():
    r = StateResolutionResult(next_state={"mood": "calm"})
    assert r.emitted_influences == ()
    assert r.emitted_events == ()
    assert r.changed is True
    assert r.trace is None


def test_process_result_defaults():
    r = ProcessResult()
    assert r.events == ()
    assert r.influences == ()
    assert r.actions == ()
    assert r.schedule_proposals == ()
    assert r.warnings == ()
    assert r.trace is None


def test_execution_and_time_context():
    ex = ExecutionContext(
        runtime_id="rt-1",
        agent_id="a-1",
        tick_id="t-1",
        plugin_id="default_life.emotion",
        process_id="emotion.decay",
        phase="internal_dynamics",
    )
    assert ex.resolution_round == 0
    tc = TimeContext(world_time=_t(), delta_time=timedelta(minutes=5))
    assert tc.delta_time == timedelta(minutes=5)
