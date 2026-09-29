"""State View / DTO（v5.9 §9.15）：Capability 返回的不可变只读视图，不暴露内部 State。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from animaflux.contracts.state import StateNamespace


@dataclass(frozen=True)
class StateView:
    """某个 Namespace 当前版本的一个不可变快照视图。data 应为不可变对象（frozen dataclass）。"""

    namespace: StateNamespace
    version: int
    data: Any
