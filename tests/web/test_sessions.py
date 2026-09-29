"""Session Registry 测试（§Web Plan §7 / §8 / §39.25）。"""

from __future__ import annotations

import threading

import pytest

from animaflux.api import AnimaFlux
from animaflux.web.sessions import SessionRegistry


def test_get_creates_life_session_lazily():
    registry = SessionRegistry(AnimaFlux())
    session = registry.get("life-1")
    assert session.handle.agent_id == "life-1"
    assert isinstance(session.lock, type(threading.Lock()))


def test_same_key_returns_same_session():
    registry = SessionRegistry(AnimaFlux())
    first = registry.get("life-1", "main")
    again = registry.get("life-1", "main")
    assert first is again


def test_different_lives_get_distinct_sessions():
    registry = SessionRegistry(AnimaFlux())
    a = registry.get("life-a")
    b = registry.get("life-b")
    assert a is not b
    assert a.handle.agent_id == "life-a"
    assert b.handle.agent_id == "life-b"


def test_non_main_branch_deferred_to_w1():
    registry = SessionRegistry(AnimaFlux())
    with pytest.raises(KeyError):
        registry.get("life-1", "branch_B")
