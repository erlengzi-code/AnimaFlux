"""Communication Process（v5.9 §14E）。

Communication 是 Process，不新增 Core State。CommunicativeIntent ≠ Utterance（§14E.1）：
Decision 决定「要不要说/说什么/透露多少」，这里把既定 Intent 转成可执行表达。
Disclosure Policy（§14E.5）：full / partial / vague / withhold / redirect。LLM 没有自主
撒谎权限（§14E.7）：Decision 只要求 withhold，就不得擅自升级成 deception。Concealment
（知道但不说）≠ Deception（故意让对方形成与自己 Belief 不一致的判断）（§14E.6）。

v0.1 为确定性模板 + 校验，无 LLM（§14E.31.6 的确定性 fallback）。
"""

from __future__ import annotations

from typing import Any

from animaflux.contracts.communication import (
    CommunicativeActionIntent,
    CommunicativeIntent,
    CommunicationValidationResult,
)
from animaflux.kernel.ids import IdGenerator

# Speech Act -> 确定性表达前缀（§14E.3 可扩展 Vocabulary，v0.1 取最小集）
SPEECH_ACT_PREFIX: dict[str, str] = {
    "APOLOGIZE": "I'm sorry.",
    "THANK": "Thank you.",
    "ASK": "Could you tell me: ",
    "REQUEST": "Please ",
    "REFUSE": "I can't do that.",
    "COMFORT": "I'm here for you. ",
    "WARN": "Please be careful: ",
    "INFORM": "",
    "PERSUADE": "I really think you should know: ",
}

# Disclosure Policy -> 保守表达（§14E.5 / §14E.27）
_WITHHOLD = "I'd rather not say."
_REDIRECT = "Let's talk about something else."
_VAGUE = "Something came up."


class CommunicationProcess:
    """把 CommunicativeIntent 转成可执行 CommunicativeActionIntent（§14E.29）。"""

    def __init__(self) -> None:
        self._ids = IdGenerator("COM", width=None)

    def realize(
        self, intent: CommunicativeIntent, *, style: Any = None, draft_text: str | None = None
    ) -> CommunicativeActionIntent:
        # draft_text 允许「language realization」可替换（§15D.3）：默认确定性 _render，
        # 亦可注入 LLM 产出的自然语句；无论如何都走同一套校验/修复（§14E.13–14E.18）。
        utterance = draft_text if draft_text is not None else self._render(intent, style)
        validation = self._validate(intent, utterance)
        repaired = False
        if not validation.passed:
            # bounded repair（§14E.18）：一次保守回退，不无限重写
            utterance = self._repair(intent)
            repaired = True
            validation = self._validate(intent, utterance)
            if not validation.passed:
                utterance = ""  # NO_UTTERANCE 优于 hallucination / 泄露（§14E.18）
        return CommunicativeActionIntent(
            intent_ref=intent.intent_ref,
            actor_ref=intent.actor_ref,
            target_refs=intent.target_refs,
            channel="text",
            speech_act=intent.speech_act,
            utterance=utterance,
            communicative_goal_refs=(intent.communicative_goal,) if intent.communicative_goal else (),
            disclosure_metadata={
                "policy": intent.disclosure_policy,
                "epistemic_stance": intent.epistemic_stance,
                "repaired": repaired,
                "validated": validation.passed,
            },
            decision_ref=intent.decision_ref,
            trace_ref=self._ids.next(),
        )

    def _render(self, intent: CommunicativeIntent, style: Any) -> str:
        policy = intent.disclosure_policy
        if policy == "withhold":
            return _WITHHOLD
        if policy == "redirect":
            return _REDIRECT
        if policy == "vague":
            return _VAGUE
        prefix = SPEECH_ACT_PREFIX.get(intent.speech_act, "")
        if policy == "partially_disclose":
            content = intent.content_intents[0] if intent.content_intents else ""
        else:
            content = " ".join(intent.content_intents)
        return f"{prefix}{content}".strip() or _VAGUE

    def _validate(self, intent: CommunicativeIntent, utterance: str) -> CommunicationValidationResult:
        checks: list[str] = []
        # Target / Channel Validity（§14E.17）
        if not intent.target_refs:
            return CommunicationValidationResult(
                passed=False, checks=("target_validity",), reason="no target"
            )
        checks.append("target_validity")
        lowered = utterance.lower()
        # Disclosure Compliance（§14E.16）：forbidden claims 不得泄露
        for claim in intent.forbidden_claims:
            if claim and claim.lower() in lowered:
                return CommunicationValidationResult(
                    passed=False,
                    checks=tuple(checks) + ("disclosure_compliance",),
                    reason="forbidden claim leaked",
                )
        checks.append("disclosure_compliance")
        # Intent Fidelity（§14E.7 / §14E.14）：withhold / vague / redirect 不得把隐瞒内容说出来
        if intent.disclosure_policy in ("withhold", "vague", "redirect"):
            for c in intent.content_intents:
                if c and c.lower() in lowered:
                    return CommunicationValidationResult(
                        passed=False,
                        checks=tuple(checks) + ("intent_fidelity",),
                        reason=f"{intent.disclosure_policy} escalated to disclosure",
                    )
        checks.append("intent_fidelity")
        # Knowledge Grounding（§14E.15）：确定性模板不引入新事实，由构造保证；此处仅登记
        checks.append("knowledge_grounding")
        return CommunicationValidationResult(passed=True, checks=tuple(checks))

    @staticmethod
    def _repair(intent: CommunicativeIntent) -> str:
        if intent.disclosure_policy == "withhold":
            return _WITHHOLD
        return _VAGUE
