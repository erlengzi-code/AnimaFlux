"""⑤ 持久化与时间线（§15 / §16C.13–17 / §21）。

Scenario：一生可回放（Checkpoint + Timeline）→ 未走的路（Branch）→ 续命（Restore / Open）。
"""

from __future__ import annotations

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.persistence.sqlite import SqliteBackend


def test_checkpoint_carries_state_and_version_map():
    """Checkpoint 快照 State + Version Map（§15.11）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-cp")
    handle.step(1.0)
    cp = handle.checkpoint()
    assert cp.agent_id == "func-cp"
    assert "identity" in cp.states
    assert "emotion" in cp.states
    assert "identity" in cp.version_map
    assert handle.list_checkpoints()[-1].checkpoint_id == cp.checkpoint_id


def test_timeline_is_read_only_replay():
    """一生可回放：timeline 只读，不产生新状态（§21.3 / §22.9）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-timeline")
    handle.send_text("I sense danger ahead.")

    ticks = handle.timeline()
    assert ticks
    # 回放后状态版本不变（只读）
    emotion_version = handle.inspect(StateNamespace.EMOTION).version
    handle.timeline()
    assert handle.inspect(StateNamespace.EMOTION).version == emotion_version


def test_branch_divergence_and_shared_prefork(make_influence):
    """未走的路：post-fork 分叉，pre-fork 共享（§21.8）。"""
    flux = AnimaFlux()
    handle = flux.create_life("func-branch")

    form = make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.form", 0.0,
        created_at=handle.now(),
        metadata={"target_id": "human-user",
                  "dimensions": {"familiarity": 0.1, "trust": 0.1, "affection": 0.05},
                  "labels": ("colleague",)},
    )
    handle.step(1.0, extra_influences=(form,))
    trust_up = make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.update", 0.3,
        created_at=handle.now(),
        metadata={"target_id": "human-user", "dimension": "trust", "delta": 0.3},
    )
    handle.step(1.0, extra_influences=(trust_up,))

    base_trust = handle.inspect(StateNamespace.RELATIONSHIP).data.relationships[0].dimensions.trust

    branch_a = handle.branch(name="supportive")
    branch_b = handle.branch(name="conflict")

    branch_a.step((make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.update", 0.2,
        created_at=handle.now(),
        metadata={"target_id": "human-user", "dimension": "affection", "delta": 0.2},
    ),))
    branch_b.step((make_influence(
        StateNamespace.RELATIONSHIP.value, "relationship.update", 0.4,
        created_at=handle.now(),
        metadata={"target_id": "human-user", "dimension": "resentment", "delta": 0.4},
    ),))

    a_rel = branch_a.read(StateNamespace.RELATIONSHIP).relationships[0]
    b_rel = branch_b.read(StateNamespace.RELATIONSHIP).relationships[0]

    assert branch_a.branch_id != branch_b.branch_id
    # post-fork 分叉
    assert a_rel.dimensions.affection > b_rel.dimensions.affection
    assert b_rel.dimensions.resentment > a_rel.dimensions.resentment
    # pre-fork 共享：trust 在两分支均未变
    assert a_rel.dimensions.trust == b_rel.dimensions.trust == base_trust


def test_two_lives_share_one_sqlite_backend():
    """同一 SQLite 后端承载多条生命（§16B.1 全局唯一版本 ID）：互不冲突。

    回归：第二条生命的 `identity_v1` 等曾与第一条冲突 → UNIQUE constraint failed。
    """
    flux = AnimaFlux(SqliteBackend(":memory:"))
    a = flux.create_life("life-a")
    b = flux.create_life("life-b")
    a.step(3600.0)
    b.step(3600.0)

    assert set(flux.list_lives()) == {"life-a", "life-b"}
    # 两条生命都能从同一后端读回并继续演化
    a2 = flux.open("life-a")
    b2 = flux.open("life-b")
    assert a2.agent_id == "life-a"
    assert b2.agent_id == "life-b"
    a2.step(60.0)
    b2.step(60.0)


def test_delete_life_removes_from_backend():
    """删除生命：从后端彻底移除（§Web Plan §10），此后 list/open 均不可见。"""
    flux = AnimaFlux(InMemoryBackend())
    flux.create_life("func-del")
    assert "func-del" in flux.list_lives()

    flux.delete_life("func-del")
    assert "func-del" not in flux.list_lives()


def test_restore_and_open_continue_same_life():
    """续命：Restore 与 Open 都能延续同一生命（§16C.14 / §21.1）。"""
    flux = AnimaFlux(InMemoryBackend())
    h1 = flux.create_life("func-open")
    h1.send_text("I sense danger ahead.")

    cp = h1.checkpoint()
    h2 = flux.restore(cp)
    assert h2.agent_id == "func-open"
    assert h2.branch_id == "main"
    h2.step(1.0)  # 可继续演化

    h3 = flux.open("func-open")
    assert h3.agent_id == "func-open"
    h3.step(1.0)
