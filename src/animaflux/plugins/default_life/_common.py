"""Default Life 插件共享工具（数值钳制 / datetime 序列化）。"""

from __future__ import annotations

from datetime import datetime


def clamp01(x: float) -> float:
    """钳制到 [0, 1]。"""
    return max(0.0, min(1.0, float(x)))


def clamp_valence(x: float) -> float:
    """钳制到 [-1, 1]。"""
    return max(-1.0, min(1.0, float(x)))


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def from_iso(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None
