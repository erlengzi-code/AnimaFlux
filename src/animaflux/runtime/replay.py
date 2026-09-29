"""Replay（v5.9 §21 / §22.9 / §22.14 Level 1）。

Exact Historical Replay 是 Read-only（§21.3）：只读取已持久化的 Commit Journal 与 State
Version，不产生新 State / Event / Memory / Schedule（§21.2），也永不重新调用 LLM / Tool /
External API（§22.9 / §22.10）——即使 Provider / Model 后续变化，历史仍可精确回放。
"""

from __future__ import annotations

from dataclasses import dataclass

from animaflux.contracts.persistence import PersistenceBackend


@dataclass(frozen=True)
class ReplayedTick:
    """一次 Tick 的只读回放视图（§21.2）。"""

    tick_id: str
    commit_id: str
    version_map: dict[str, str]
    runtime_time_after: str | None
    payloads: dict[str, dict | None]   # namespace -> 已持久化的 payload（历史原样）


class ReplayEngine:
    """只读回放 Commit Journal + State Version（§22.14 Level 1）。"""

    def __init__(self, backend: PersistenceBackend) -> None:
        self._backend = backend
        # 契约计数器：Exact Replay 永不回拨 LLM（§21.1 / §22.9）
        self.llm_calls = 0
        # 契约计数器：Exact Replay 不产生任何写入（§21.2 / §21.3）
        self.write_ops = 0

    def replay_timeline(self, agent_id: str) -> tuple[ReplayedTick, ...]:
        """按 Commit Journal 顺序重建历史时间线，只读、不重放非确定性边界。"""
        ticks = []
        for commit in self._backend.list_commits(agent_id):
            payloads: dict[str, dict | None] = {}
            for namespace, state_version_id in commit.version_map.items():
                rec = self._backend.read_version(state_version_id)
                payloads[namespace] = rec.payload if rec is not None else None
            ticks.append(
                ReplayedTick(
                    tick_id=commit.tick_id,
                    commit_id=commit.commit_id,
                    version_map=dict(commit.version_map),
                    runtime_time_after=commit.runtime_time_after,
                    payloads=payloads,
                )
            )
        return tuple(ticks)
