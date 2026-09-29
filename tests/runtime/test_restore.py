"""P10 RESTORE 测试（§21.1：RESTORE / REPLAY / RESIMULATE-BRANCH 三种语义严格区分）。"""

from datetime import datetime

from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.plugins.default_life import register_default_life
from animaflux.plugins.default_life.body import BodyState
from animaflux.plugins.default_life.emotion import EmotionState
from animaflux.plugins.default_life.identity import IdentityState
from animaflux.runtime.branch import fork
from animaflux.runtime.lifeloop import LifeRuntime
from animaflux.runtime.restore import restore


def _base() -> LifeRuntime:
    runtime = LifeRuntime("agent-1", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    register_default_life(runtime)
    runtime.seed(StateNamespace.IDENTITY, IdentityState(birth_time=datetime(1980, 1, 1), primary_name="小林"))
    runtime.seed(StateNamespace.BODY, BodyState())
    runtime.seed(StateNamespace.EMOTION, EmotionState())
    return runtime


def test_restore_reloads_committed_state_same_agent():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    restored = restore(checkpoint, registry=runtime.registry)
    # 同一 agent 上重建已提交状态，不创建新 branch（§21.1 RESTORE）
    assert restored.agent_id == "agent-1"
    assert restored.read(StateNamespace.EMOTION) == checkpoint.states["emotion"]
    assert not hasattr(restored, "record")  # 与 fork 不同：无 BranchRecord


def test_restore_distinct_from_branch():
    runtime = _base()
    checkpoint = runtime.checkpoint()
    restored = restore(checkpoint, registry=runtime.registry)
    branch = fork(checkpoint, registry=runtime.registry, branch_name="A")
    # RESTORE 无 branch_id；RESIMULATE-BRANCH 有 branch_id（§21.1 严格区分）
    assert not hasattr(restored, "record")
    assert hasattr(branch, "record")
    assert branch.record.branch_id.startswith("BR-")
