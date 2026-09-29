"""P8 Communication Process 测试（§14E：Intent≠Utterance / Disclosure / 无自主撒谎）。"""

from animaflux.contracts.communication import CommunicativeIntent
from animaflux.plugins.default_cognition.communication import CommunicationProcess


def _intent(**kw):
    defaults = dict(intent_ref="I-1", actor_ref="A", target_refs=("B",))
    defaults.update(kw)
    return CommunicativeIntent(**defaults)


def test_intent_and_utterance_are_separate():
    proc = CommunicationProcess()
    intent = _intent(speech_act="INFORM", content_intents=("明天会下雨",))
    action = proc.realize(intent)
    assert action.utterance == "明天会下雨"       # Utterance = 具体怎么说
    assert intent.content_intents == ("明天会下雨",)  # Intent 仍是「想表达什么」（§14E.1）
    assert action.speech_act == "INFORM"


def test_fully_disclose_includes_content():
    proc = CommunicationProcess()
    action = proc.realize(_intent(disclosure_policy="fully_disclose", content_intents=("我饿了",)))
    assert "我饿了" in action.utterance


def test_withhold_does_not_leak():
    proc = CommunicationProcess()
    intent = _intent(
        disclosure_policy="withhold",
        content_intents=("我看见了秘密",),
        forbidden_claims=("秘密",),
    )
    action = proc.realize(intent)
    assert "秘密" not in action.utterance
    assert action.utterance == "I'd rather not say."


def test_llm_no_autonomous_lying():
    proc = CommunicationProcess()
    # Decision 只要求 withhold，realize 不得擅自升级为相反的断言（deception，§14E.7）
    intent = _intent(disclosure_policy="withhold", content_intents=("我去过那里",))
    action = proc.realize(intent)
    assert action.utterance == "I'd rather not say."  # Concealment，非 Deception（§14E.6）
    assert "去过" not in action.utterance


def test_forbidden_claim_triggers_bounded_repair():
    proc = CommunicationProcess()
    intent = _intent(
        speech_act="INFORM",
        content_intents=("我知道密码123",),
        forbidden_claims=("密码123",),
    )
    action = proc.realize(intent)
    assert "密码123" not in action.utterance  # 泄露被修掉（§14E.18）
    assert action.disclosure_metadata["repaired"] is True


def test_no_target_is_no_utterance():
    proc = CommunicationProcess()
    intent = CommunicativeIntent(intent_ref="I-1", actor_ref="A", target_refs=())
    action = proc.realize(intent)
    assert action.utterance == ""  # 无接收者 → NO_UTTERANCE（§14E.17）
