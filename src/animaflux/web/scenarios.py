"""Scenario Registry（§12E / Web Plan 增补）。

进程内维护 life_id → (ScenarioEnvironment, scenario_type) 的映射。场景 world 是「外部世界事实」，
**不进 StateStore、不可持久化**（§12E 铁律）：服务重启后 world 事实与场景类型映射都重置，与
checkpoint/branch 的「进程内跟踪（§Web Plan §7/§14）」一致，作为 v0.1 限制记录。

每生命独立 world（不是 flux 全局共享）：建生命时经 Public Facade 的
`animaflux.api.build_scenario_environment` 实例化，`open`/`restore` 复用同一实例，使世界事实
在生命重新打开后继续累积。本模块不 import Core 内部，只持有映射（§Web Plan §2/§10）。
"""

from __future__ import annotations

import threading


class ScenarioRegistry:
    """life_id → (env, scenario_type) 的进程内注册表（线程安全）。"""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[object, str]] = {}
        self._guard = threading.Lock()

    def register(self, life_id: str, env, scenario_type: str) -> None:
        with self._guard:
            self._entries[life_id] = (env, scenario_type)

    def get(self, life_id: str):
        with self._guard:
            entry = self._entries.get(life_id)
            return entry if entry is not None else (None, None)

    def remove(self, life_id: str) -> None:
        with self._guard:
            self._entries.pop(life_id, None)
