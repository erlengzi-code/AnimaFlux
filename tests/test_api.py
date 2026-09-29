"""Public API（AnimaFlux / LifeHandle）测试（§16C）。"""

from datetime import datetime

from animaflux.api import AnimaFlux, CharacterBootstrap, LifeHandle
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.persistence.sqlite import SqliteBackend


def test_create_life_seeds_core_states():
    flux = AnimaFlux()
    handle = flux.create_life(
        "life-1",
        bootstrap=CharacterBootstrap(primary_name="小林", values=("growth", "care")),
    )
    assert isinstance(handle, LifeHandle)
    assert handle.agent_id == "life-1"
    assert handle.branch_id == "main"

    identity = handle.inspect(StateNamespace.IDENTITY).data
    assert identity.primary_name == "小林"
    values = handle.inspect(StateNamespace.VALUE).data
    assert {v.value_type for v in values.commitments} == {"growth", "care"}


def test_send_text_full_cognition_never_llm():
    flux = AnimaFlux()
    handle = flux.create_life("life-1")
    result = handle.send_text("I sense danger ahead.")

    assert result.committed is True
    assert result.tick_id is not None
    assert result.text  # 非空 utterance
    # 完整 Cognition：威胁 → fear 情绪落地
    emotion = handle.inspect(StateNamespace.EMOTION).data
    assert any(e.emotion_type == "fear" for e in emotion.episodes)


def test_inspect_returns_immutable_view():
    flux = AnimaFlux()
    handle = flux.create_life("life-1")
    view = handle.inspect(StateNamespace.IDENTITY)
    assert view.namespace == StateNamespace.IDENTITY
    assert view.version == 1


def test_checkpoint_carries_states_and_version_map():
    flux = AnimaFlux()
    handle = flux.create_life("life-1")
    handle.step(1.0)
    cp = handle.checkpoint()
    assert cp.agent_id == "life-1"
    assert "identity" in cp.states
    assert "emotion" in cp.states
    assert "identity" in cp.version_map


def test_branch_returns_distinct_handles():
    flux = AnimaFlux()
    handle = flux.create_life("life-1")
    a = handle.branch(name="A")
    b = handle.branch(name="B")
    assert a.branch_id != b.branch_id
    assert a.agent_id == "life-1" == b.agent_id


def test_restore_continues_same_agent():
    flux = AnimaFlux()
    h1 = flux.create_life("life-1")
    h1.step(1.0)
    cp = h1.checkpoint()

    h2 = flux.restore(cp)
    assert h2.agent_id == "life-1"
    assert h2.branch_id == "main"
    # 恢复后可继续演化
    h2.step(1.0)


def test_open_reconstructs_and_continues_from_backend():
    flux = AnimaFlux(InMemoryBackend())
    h1 = flux.create_life("life-1", bootstrap=CharacterBootstrap(primary_name="小林"))
    h1.step(1.0)
    assert h1.inspect(StateNamespace.BODY).version == 2

    h2 = flux.open("life-1")
    assert h2.agent_id == "life-1"
    assert h2.branch_id == "main"
    assert h2.inspect(StateNamespace.IDENTITY).data.primary_name == "小林"
    # 继续演化不冲突，产生下一个 tick（t2）
    assert h2.step(1.0) == "t2"


def test_open_works_with_sqlite_backend():
    backend = SqliteBackend(":memory:")
    flux = AnimaFlux(backend)
    h1 = flux.create_life("life-1")
    h1.step(60.0)

    h2 = flux.open("life-1")
    assert h2.inspect(StateNamespace.IDENTITY).version == 1
    h2.step(60.0)
    backend.close()
