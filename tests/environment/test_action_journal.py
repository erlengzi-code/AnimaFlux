"""External Action Journal 测试（§15B.17 幂等 / §12C 外部副作用边界）。"""

from datetime import datetime

from animaflux.contracts.environment import ActionIntent, ActionResult
from animaflux.environment.action_journal import ExternalActionJournal


class _RecordingEnvironment:
    def __init__(self) -> None:
        self.submissions = 0

    def submit_action(self, intent: ActionIntent) -> ActionResult:
        self.submissions += 1
        return ActionResult(
            result_id=f"R{self.submissions}",
            intent_id=intent.intent_id,
            status="success",
            world_time=datetime(2000, 1, 1),
        )


def _intent(intent_id: str = "ACT-1") -> ActionIntent:
    return ActionIntent(
        intent_id=intent_id,
        actor="agent-1",
        action_type="send_message",
        world_time=datetime(2000, 1, 1),
        content="hi",
    )


def test_idempotent_submit_reuses_result():
    env = _RecordingEnvironment()
    journal = ExternalActionJournal(env)

    r1 = journal.submit(_intent("ACT-1"))
    r2 = journal.submit(_intent("ACT-1"))  # 技术重试：同一 action_id 幂等复用

    assert r1.result_id == r2.result_id
    assert env.submissions == 1  # 外部副作用只执行一次（§15B.17）
    assert journal.executed_count() == 1


def test_distinct_intents_execute_separately():
    env = _RecordingEnvironment()
    journal = ExternalActionJournal(env)

    journal.submit(_intent("ACT-A"))
    journal.submit(_intent("ACT-B"))

    assert env.submissions == 2
    assert journal.executed_count() == 2
