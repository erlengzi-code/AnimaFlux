"""P2 Kernel 注册表测试（§9.7 Capability Registry / §3.3 Namespace）。"""

import pytest

from animaflux.kernel.registry import CapabilityRegistry, NamespaceRegistry


class FakeProvider:
    def __init__(self, name: str) -> None:
        self.name = name


def test_capability_register_and_get_primary():
    reg = CapabilityRegistry()
    p1 = FakeProvider("openai")
    p2 = FakeProvider("claude")
    reg.register("llm.chat", p1)
    reg.register("llm.chat", p2)
    assert reg.get("llm.chat") is p1  # first = primary（§9.8 不随机选择）
    assert set(reg.providers("llm.chat")) == {p1, p2}
    assert reg.has("llm.chat") is True


def test_capability_get_missing_raises():
    reg = CapabilityRegistry()
    with pytest.raises(KeyError):
        reg.get("memory.search")


def test_namespace_owner_single_and_lookup():
    reg = NamespaceRegistry()
    owner = object()
    reg.register_owner("emotion", owner)
    assert reg.get_owner("emotion") is owner
    assert "emotion" in reg.namespaces()


def test_namespace_duplicate_owner_raises():
    reg = NamespaceRegistry()
    reg.register_owner("emotion", object())
    with pytest.raises(ValueError):
        reg.register_owner("emotion", object())
