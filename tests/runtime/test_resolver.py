"""P3 State Resolver 测试（§7 分组 / Resolution Round / Deferred Influence / 确定性 / 异常）。"""

from datetime import datetime, timedelta

import pytest

from animaflux.contracts.context import ExecutionContext, TimeContext
from animaflux.contracts.influence import Influence
from animaflux.contracts.state import StateNamespace, StateResolutionResult
from animaflux.kernel.random import RandomService
from animaflux.kernel.registry import CapabilityRegistry, NamespaceRegistry
from animaflux.runtime.context import RuntimeContextImpl
from animaflux.runtime.resolver import InfluenceBuffer, StateResolver
from animaflux.state.state_store import StateStore

EMOTION = StateNamespace.EMOTION
BODY = StateNamespace.BODY
T0 = datetime(2000, 1, 1)


def _ctx() -> RuntimeContextImpl:
    return RuntimeContextImpl(
        execution=ExecutionContext(
            runtime_id="r", agent_id="a", tick_id="t1",
            plugin_id="p", process_id="pr", phase="test",
        ),
        time=TimeContext(world_time=T0, delta_time=timedelta(seconds=1)),
        random=RandomService(root_seed=0),
        capabilities=CapabilityRegistry(),
    )


def _inf(influence_id: str, target: str, *, source: str = "p", at: datetime | None = None) -> Influence:
    return Influence(
        influence_id=influence_id,
        source_plugin=source,
        target_state=target,
        influence_type="x",
        magnitude=0.5,
        created_at=at or T0,
    )


# --- 分组 / 路由 ---

def test_routes_to_target_primary_owner_not_source():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)
    store.seed(BODY, 0.0)

    calls = {"emotion": [], "body": []}

    class Owner:
        def __init__(self, ns):
            self.ns = ns

        def resolve(self, cur, infs, ctx):
            calls[self.ns].append(infs)
            return StateResolutionResult(next_state=cur, changed=False)

    registry.register_owner(EMOTION, Owner("emotion"))
    registry.register_owner(BODY, Owner("body"))

    resolver = StateResolver(store, registry)
    store.begin_tick()
    inf = _inf("INF-1", "emotion", source="body_owner")
    outcome = resolver.resolve([inf], _ctx())

    assert outcome.ok
    assert calls["emotion"] == [(inf,)]  # 路由到 emotion 的 owner
    assert calls["body"] == []  # 不是 source 的 owner


def test_batches_all_influences_per_owner_per_round():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)

    received = []

    class Owner:
        def resolve(self, cur, infs, ctx):
            received.append(tuple(sorted(i.influence_id for i in infs)))
            return StateResolutionResult(next_state=cur, changed=False)

    registry.register_owner(EMOTION, Owner())
    resolver = StateResolver(store, registry)
    store.begin_tick()
    resolver.resolve([_inf("INF-3", "emotion"), _inf("INF-1", "emotion"), _inf("INF-2", "emotion")], _ctx())

    # §7.5：一个 Round 内一个 State 只 resolve 一次，收齐全部 Influence
    assert received == [("INF-1", "INF-2", "INF-3")]


# --- Resolution Round ---

def test_emitted_influences_trigger_next_round():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)
    store.seed(BODY, 0.0)

    body_calls = []

    class EmotionOwner:
        def resolve(self, cur, infs, ctx):
            emit = _inf("INF-E", "body", source="emotion_owner")
            return StateResolutionResult(next_state=cur + 1, emitted_influences=(emit,))

    class BodyOwner:
        def resolve(self, cur, infs, ctx):
            body_calls.append(infs)
            return StateResolutionResult(next_state=cur, changed=False)

    registry.register_owner(EMOTION, EmotionOwner())
    registry.register_owner(BODY, BodyOwner())
    resolver = StateResolver(store, registry)
    store.begin_tick()
    outcome = resolver.resolve([_inf("INF-1", "emotion")], _ctx())

    assert outcome.rounds_run == 2
    assert body_calls  # body 在第二轮被触发


def test_no_new_influence_stops_early():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)

    class Owner:
        def resolve(self, cur, infs, ctx):
            return StateResolutionResult(next_state=cur, changed=False)

    registry.register_owner(EMOTION, Owner())
    resolver = StateResolver(store, registry, max_rounds=3)
    store.begin_tick()
    outcome = resolver.resolve([_inf("INF-1", "emotion")], _ctx())
    assert outcome.rounds_run == 1  # §7.9：无新 Influence 提前停止


# --- Deferred Influence Queue ---

def test_max_rounds_defers_overflow():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)
    n = 0

    class InfiniteOwner:
        def resolve(self, cur, infs, ctx):
            nonlocal n
            n += 1
            emit = _inf(f"INF-{n}", "emotion")
            return StateResolutionResult(next_state=cur, emitted_influences=(emit,))

    registry.register_owner(EMOTION, InfiniteOwner())
    resolver = StateResolver(store, registry, max_rounds=3)
    store.begin_tick()
    outcome = resolver.resolve([_inf("INF-0", "emotion")], _ctx())

    assert outcome.rounds_run == 3
    assert outcome.deferred_count == 1  # 第 3 轮新 Influence 进入 deferred
    assert resolver.deferred_count == 1


def test_deferred_processed_next_tick():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)

    processed = []

    class Owner:
        def resolve(self, cur, infs, ctx):
            processed.extend(i.influence_id for i in infs)
            return StateResolutionResult(
                next_state=cur,
                emitted_influences=tuple(_inf(f"{i.influence_id}-out", "emotion") for i in infs),
            )

    registry.register_owner(EMOTION, Owner())
    resolver = StateResolver(store, registry, max_rounds=1)
    store.begin_tick()
    out1 = resolver.resolve([_inf("A", "emotion")], _ctx())
    assert out1.deferred_count == 1

    store.begin_tick()  # 下一 Tick
    resolver.resolve([], _ctx())
    assert "A-out" in processed  # deferred 被重新处理


# --- 确定性 / 异常 ---

def test_arrival_order_does_not_change_result():
    def run(order):
        registry = NamespaceRegistry()
        store = StateStore("a", registry)
        store.seed(EMOTION, 0.0)
        received = []

        class Owner:
            def resolve(self, cur, infs, ctx):
                received.append(tuple(i.influence_id for i in infs))
                return StateResolutionResult(next_state=cur + sum(i.magnitude for i in infs))

        registry.register_owner(EMOTION, Owner())
        resolver = StateResolver(store, registry)
        store.begin_tick()
        infs = [_inf("A", "emotion"), _inf("B", "emotion"), _inf("C", "emotion")]
        resolver.resolve([infs[i] for i in order], _ctx())
        store.commit()
        return store.read(EMOTION), received

    v1, r1 = run([0, 1, 2])
    v2, r2 = run([2, 0, 1])
    assert v1 == v2  # 结果不受到达顺序影响
    assert r1 == r2 == [("A", "B", "C")]  # Owner 收到的顺序稳定


def test_owner_exception_fails_tick_no_commit():
    registry = NamespaceRegistry()
    store = StateStore("a", registry)
    store.seed(EMOTION, 0.0)

    class BrokenOwner:
        def resolve(self, cur, infs, ctx):
            raise RuntimeError("boom")

    registry.register_owner(EMOTION, BrokenOwner())
    resolver = StateResolver(store, registry)
    store.begin_tick()
    outcome = resolver.resolve([_inf("A", "emotion")], _ctx())

    assert outcome.ok is False
    assert outcome.error == "boom"
    assert store.committed_version(EMOTION).version == 1  # 未 commit


def test_influence_buffer_drain():
    buf = InfluenceBuffer()
    buf.add(_inf("A", "emotion"))
    buf.add_many([_inf("B", "emotion")])
    assert len(buf) == 2
    drained = buf.drain()
    assert len(drained) == 2
    assert len(buf) == 0
