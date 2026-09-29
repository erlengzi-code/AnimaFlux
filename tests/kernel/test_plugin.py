"""P2 Kernel Plugin 管理测试（§11 Manifest / Lifecycle / 校验 / 依赖图）。"""

from dataclasses import FrozenInstanceError

import pytest

from animaflux.kernel.plugin import Plugin, PluginManager, PluginManifest


def _m(plugin_id: str, **kw) -> PluginManifest:
    defaults = dict(name=plugin_id, version="1.0.0", kernel_compatibility="v0.1")
    defaults.update(kw)
    return PluginManifest(plugin_id=plugin_id, **defaults)


def test_manifest_is_frozen():
    with pytest.raises(FrozenInstanceError):
        _m("a").plugin_id = "b"  # type: ignore[misc]


def test_add_and_duplicate_rejected():
    pm = PluginManager()
    pm.add(Plugin(_m("a")))
    with pytest.raises(ValueError):
        pm.add(Plugin(_m("a")))


def test_validate_no_errors_for_clean_set():
    pm = PluginManager()
    pm.add(Plugin(_m("emotion", owns_states=("emotion",))))
    assert pm.validate() == []


def test_owner_conflict_detected():
    pm = PluginManager()
    pm.add(Plugin(_m("a", owns_states=("emotion",))))
    pm.add(Plugin(_m("b", owns_states=("emotion",))))
    assert any("emotion" in e for e in pm.validate())


def test_task_type_conflict_detected():
    pm = PluginManager()
    pm.add(Plugin(_m("a", task_types=("reflection.daily",))))
    pm.add(Plugin(_m("b", task_types=("reflection.daily",))))
    assert any("reflection.daily" in e for e in pm.validate())


def test_required_capability_missing():
    pm = PluginManager()
    pm.add(Plugin(_m("a", requires_capabilities=("memory.search",))))
    assert any("memory.search" in e for e in pm.validate())


def test_required_capability_satisfied():
    pm = PluginManager()
    pm.add(Plugin(_m("memory", provides_capabilities=("memory.search",))))
    pm.add(Plugin(_m("reflection", requires_capabilities=("memory.search",))))
    assert pm.validate() == []


def test_dependency_cycle_detected():
    pm = PluginManager()
    pm.add(Plugin(_m("a", provides_capabilities=("x",), requires_capabilities=("y",))))
    pm.add(Plugin(_m("b", provides_capabilities=("y",), requires_capabilities=("x",))))
    assert any("cycle" in e for e in pm.validate())


def test_topological_order_dependencies_first():
    pm = PluginManager()
    pm.add(Plugin(_m("memory", provides_capabilities=("memory.search",))))
    pm.add(Plugin(_m("reflection", requires_capabilities=("memory.search",))))
    order = pm.ordered_plugin_ids()
    assert order.index("memory") < order.index("reflection")
