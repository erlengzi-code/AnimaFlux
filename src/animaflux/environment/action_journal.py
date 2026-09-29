"""External Action Journal（v5.9 §12C / §15B.17 / §15B.18）。

External Action 是外部副作用边界（§15B.17）：内部 Tick Transaction Rollback 不代表外部世界
可以 Rollback。Action 用稳定 action_id / correlation_id 标识；技术性 Tick Retry 不应重复
执行已经成功的外部动作——如环境支持，用幂等（idempotency）复用已记录的结果。
"""

from __future__ import annotations

from dataclasses import dataclass

from animaflux.contracts.environment import ActionIntent, ActionResult, EnvironmentAdapter


@dataclass(frozen=True)
class ExternalActionRecord:
    """一条已执行外部动作的 Journal 记录（§15B.17）。"""

    action_id: str
    attempt_id: str
    intent: ActionIntent
    result: ActionResult
    status: str = "EXECUTED"


class ExternalActionJournal:
    """包装 Environment Adapter：执行外部动作并按 action_id 幂等复用结果（§15B.17）。"""

    def __init__(self, environment: EnvironmentAdapter) -> None:
        self._env = environment
        self._executed: dict[str, ActionResult] = {}

    def submit(self, intent: ActionIntent) -> ActionResult:
        # 幂等：同一 action_id 已成功执行 → 复用结果，不重复外部副作用（§15B.17）
        existing = self._executed.get(intent.intent_id)
        if existing is not None:
            return existing
        result = self._env.submit_action(intent)
        self._executed[intent.intent_id] = result
        return result

    def executed_count(self) -> int:
        return len(self._executed)
