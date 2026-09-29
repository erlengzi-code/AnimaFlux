"""Communication 契约（v5.9 §14E）。

Communication 是 Process，不新增 Core State。CommunicativeIntent ≠ Utterance（§14E.1）。
Decision 决定「要不要说/说什么/透露多少」，Communication 把既定 Intent 转成可执行表达。
标准输出 CommunicativeActionIntent（§14E.29）交给 Environment Adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommunicativeIntent:
    """Decision 产出的交流意图（§14E.2）。"""

    intent_ref: str
    actor_ref: str
    target_refs: tuple[str, ...] = ()
    speech_act: str = "INFORM"
    communicative_goal: str | None = None
    content_intents: tuple[str, ...] = ()
    disclosure_policy: str = "fully_disclose"  # fully_disclose | partially_disclose | vague | withhold | redirect
    epistemic_stance: str = "believed"
    style_constraints: tuple[str, ...] = ()
    allowed_claims: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    decision_ref: str | None = None


@dataclass(frozen=True)
class CommunicativeActionIntent:
    """Communication 的标准输出（§14E.29），是交给 Environment 的动作意图。"""

    intent_ref: str
    actor_ref: str
    target_refs: tuple[str, ...] = ()
    channel: str = "text"
    speech_act: str = "INFORM"
    utterance: str = ""
    claim_refs: tuple[str, ...] = ()
    communicative_goal_refs: tuple[str, ...] = ()
    disclosure_metadata: dict = field(default_factory=dict)
    decision_ref: str | None = None
    trace_ref: str | None = None


@dataclass(frozen=True)
class CommunicationValidationResult:
    """Draft 校验结果（§14E.13）。"""

    passed: bool
    checks: tuple[str, ...] = ()
    repaired: bool = False
    reason: str | None = None
