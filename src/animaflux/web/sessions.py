"""Session Registry（§Web Plan §7 / §8 / §39.25）。

进程内维护 (agent_id, branch_id) → LifeSession（LifeHandle + threading.Lock）。单写者保证：
同一 (agent_id, branch_id) 在同一进程内只有一个活跃 handle，避免重复 open 导致 commit_id 冲突
（§8）。懒加载 + 每 Life+Branch 一把锁；本地 v0.1 无自动淘汰（§39.25）。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from animaflux.api import AnimaFlux, LifeHandle


@dataclass
class LifeSession:
    handle: LifeHandle
    lock: threading.Lock


class SessionRegistry:
    def __init__(self, flux: AnimaFlux, scenarios=None) -> None:
        self._flux = flux
        self._scenarios = scenarios
        self._sessions: dict[tuple[str, str], LifeSession] = {}
        self._guard = threading.Lock()

    def get(self, life_id: str, branch_id: str = "main") -> LifeSession:
        key = (life_id, branch_id)
        with self._guard:
            session = self._sessions.get(key)
            if session is None:
                session = self._create(life_id, branch_id)
                self._sessions[key] = session
            return session

    def _create(self, life_id: str, branch_id: str) -> LifeSession:
        if branch_id != "main":
            # v0.1 只物化 main 分支；其它 branch 的 LifeHandle 在 W1 补齐（§Web Plan §39.25）
            raise KeyError(branch_id)
        environment = None
        if self._scenarios is not None:
            environment, _scenario_type = self._scenarios.get(life_id)
        handle = self._flux.open(life_id, environment=environment)
        return LifeSession(handle=handle, lock=threading.Lock())

    def remove(self, life_id: str) -> None:
        """删除生命时淘汰其进程内 Session（§Web Plan §10），避免旧 handle 继续演化。"""
        with self._guard:
            for key in [k for k in self._sessions if k[0] == life_id]:
                self._sessions.pop(key, None)
