"""State Schema Migration 契约测试（§16D.21）。"""

import pytest

from animaflux.persistence.migration import (
    CURRENT_SCHEMA_VERSION,
    CompatibilityError,
    migrate_payload,
)


def test_current_schema_payload_passes_through():
    payload = {"joy": 0.5, "_schema_version": CURRENT_SCHEMA_VERSION}
    migrated = migrate_payload(payload)
    assert migrated == {"joy": 0.5}
    assert "_schema_version" not in migrated


def test_unmarked_payload_treated_as_current():
    # 无版本标记视为当前（v1），向前兼容旧数据（§16D.21）
    assert migrate_payload({"joy": 0.5}) == {"joy": 0.5}


def test_unsupported_future_schema_raises_explicit_error():
    with pytest.raises(CompatibilityError):
        migrate_payload({"_schema_version": 99, "joy": 0.5})


def test_unsupported_legacy_schema_raises_explicit_error():
    with pytest.raises(CompatibilityError):
        migrate_payload({"_schema_version": 0, "joy": 0.5})


def test_invalid_version_marker_raises():
    with pytest.raises(CompatibilityError):
        migrate_payload({"_schema_version": "one", "joy": 0.5})


def test_old_schema_payload_deserializes_forward_compatible():
    """旧 Schema 缺少后来新增的 optional 字段（如 status）→ 反序列化用默认值，不静默猜错。"""
    from animaflux.plugins.default_life.emotion import deserialize as emotion_deserialize

    # 旧 payload：episode 无 status / trigger_refs 字段
    old_payload = {
        "episodes": [
            {
                "episode_id": "e1", "emotion_type": "joy", "intensity": 0.5,
                "valence": 0.8, "arousal": 0.6,
                "started_at": "2000-01-01T00:00:00", "last_updated_at": "2000-01-01T00:00:01",
            }
        ],
        "mood": {"valence": 0.0, "arousal": 0.0},
    }
    state = emotion_deserialize(migrate_payload(old_payload))
    assert state.episodes[0].status == "active"  # 新增字段用默认值
    assert state.episodes[0].trigger_refs == ()
