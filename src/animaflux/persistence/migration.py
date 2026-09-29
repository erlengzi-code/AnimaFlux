"""State Schema Migration（v5.9 §16D.21）。

旧支持的 Schema 显式迁移到当前 Schema；不支持的旧 Schema 显式抛 CompatibilityError。
禁止静默猜测。v0.1 只有 Schema v1，本模块提供迁移边界与失败契约，供后续版本扩展迁移步骤。
"""

from __future__ import annotations

from typing import Any

CURRENT_SCHEMA_VERSION = 1


class CompatibilityError(Exception):
    """旧 Schema 无法安全迁移时显式抛出（§16D.21），禁止静默猜测。"""


def migrate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """把一条 State payload 迁移到当前 Schema 版本。

    - 无版本标记视为 v1（当前），原样返回（去掉内部标记）；
    - 高于当前版本的 schema 或未知 legacy schema 显式 CompatibilityError。
    """
    version = payload.get("_schema_version", CURRENT_SCHEMA_VERSION)
    if not isinstance(version, int):
        raise CompatibilityError(f"invalid schema version marker {version!r}")
    if version > CURRENT_SCHEMA_VERSION:
        raise CompatibilityError(
            f"payload schema v{version} is newer than supported v{CURRENT_SCHEMA_VERSION}"
        )
    if version < 1:
        raise CompatibilityError(f"unsupported legacy schema v{version}")
    migrated = dict(payload)
    migrated.pop("_schema_version", None)
    return migrated
