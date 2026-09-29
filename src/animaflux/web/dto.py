"""Web DTO / 序列化（§Web Plan §15 / §16 / §28）。

Core 不为了 HTTP 修改 Domain Model；Web 自己把 frozen dataclass / Enum / datetime / timedelta
递归转成 JSON-safe dict。Persistence Serializer ≠ Web Serializer（§15）：这里绝不复用 Owner 的
serialize 回调（那是持久化 payload），而是从公开 StateView.data / Public View 派生。
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


def to_jsonable(value: Any) -> Any:
    """把公开只读 View 递归转成 JSON-safe 结构（不处理 Core 私有对象）。"""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: to_jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in value]
    return str(value)


def envelope_ok(data: Any, *, request_id: str | None = None, trace_ref: str | None = None) -> dict:
    """成功 Response Envelope（§Web Plan §16）。"""
    return {
        "data": to_jsonable(data),
        "meta": {"request_id": request_id, "trace_ref": trace_ref},
    }


def envelope_err(code: str, message: str, *, request_id: str | None = None) -> dict:
    """错误 Response Envelope（§Web Plan §16），不返回内部堆栈。"""
    return {
        "error": {"code": code, "message": message},
        "meta": {"request_id": request_id, "trace_ref": None},
    }
