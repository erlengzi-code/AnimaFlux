"""Belief State Owner（v5.9 §13G）。

Belief = 我现在认为什么是真的（Subjective Truth，§13G.1）。Memory ≠ Belief（§13G.2）；
Belief ≠ Value（§13G.3）。Confidence ≠ Stability（§13G.7）：Confidence 是当前有多信，
Stability 是有多难被新证据改变。Formation / Update 必须 Evidence-driven（§13G.11）。
旧 Belief 不直接 DELETE（§13G.13）；Revision 保留历史（§13G.14）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_FORM = "belief.form"
INFLUENCE_EVIDENCE = "belief.evidence"
INFLUENCE_REVISE = "belief.revise"
INFLUENCE_OBSOLETE = "belief.obsolete"
INFLUENCE_ACTIVATE = "belief.activate"

# 无证据支撑的 Belief 只能作为低置信 Hypothesis（§13G.27 / §13G.44）
HYPOTHESIS_CONFIDENCE_CAP = 0.3
# 反证把 confidence 压到该阈值以下即 WEAKENED（§13G.13）
WEAKENED_THRESHOLD = 0.3
# 反证把 confidence 压到该阈值以下即 REJECTED
REJECTED_THRESHOLD = 0.1


@dataclass(frozen=True)
class BeliefEvidence:
    """一条证据（§13G.11）：support / contradict / qualify。"""

    evidence_id: str
    source_type: str
    support: str = "support"  # support | contradict | qualify
    source_ref: str | None = None
    reliability: float = 0.5
    directness: float = 0.5
    at: datetime | None = None


@dataclass(frozen=True)
class BeliefRecord:
    """我当前相信什么（§13G.6）。"""

    belief_id: str
    proposition: str
    confidence: float = 0.5
    stability: float = 0.5
    activation: float = 0.0
    evidence: tuple[BeliefEvidence, ...] = ()
    status: str = "ACTIVE"  # ACTIVE | WEAKENED | REJECTED | SUPERSEDED | DORMANT | OBSOLETE
    scope: str | None = None
    belief_type: str | None = None
    revision: int = 1
    history: tuple[str, ...] = ()
    formed_at: datetime | None = None
    last_updated_at: datetime | None = None


@dataclass(frozen=True)
class BeliefState:
    records: tuple[BeliefRecord, ...] = ()


def validate(state: BeliefState) -> None:
    for b in state.records:
        if not (0.0 <= b.confidence <= 1.0):
            raise ValueError(f"belief {b.belief_id} confidence out of range")
        if not (0.0 <= b.stability <= 1.0):
            raise ValueError(f"belief {b.belief_id} stability out of range")


class BeliefOwner:
    """Belief 的 Primary Owner。Evidence-driven，确定性更新（§13G.11 / §13G.27）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_FORM:
                state = self._form(state, inf)
                changes.append("form")
            elif t == INFLUENCE_EVIDENCE:
                state = self._evidence(state, inf)
                changes.append("evidence")
            elif t == INFLUENCE_REVISE:
                state = self._revise(state, inf)
                changes.append("revise")
            elif t == INFLUENCE_OBSOLETE:
                state = self._set_status(state, inf, "OBSOLETE")
                changes.append("obsolete")
            elif t == INFLUENCE_ACTIVATE:
                state = self._activate(state, inf)
                changes.append("activate")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _form(self, state: BeliefState, inf) -> BeliefState:
        proposition = str(inf.metadata.get("proposition", ""))
        evidence = self._evidence_from_metadata(inf)
        confidence = clamp01(float(inf.metadata.get("confidence", 0.5)))
        if not evidence:
            # §13G.44：无证据支撑 → 只能作为低置信 Hypothesis
            confidence = min(confidence, HYPOTHESIS_CONFIDENCE_CAP)
        stability = clamp01(float(inf.metadata.get("stability", 0.5)))
        now = inf.created_at
        record = BeliefRecord(
            belief_id=inf.influence_id, proposition=proposition, confidence=confidence,
            stability=stability, activation=1.0, evidence=evidence,
            scope=inf.metadata.get("scope"), belief_type=inf.metadata.get("belief_type"),
            formed_at=now, last_updated_at=now,
        )
        return replace(state, records=state.records + (record,))

    def _evidence(self, state: BeliefState, inf) -> BeliefState:
        belief_id = inf.metadata.get("belief_id")
        support = inf.metadata.get("support", "support")
        reliability = clamp01(float(inf.metadata.get("reliability", 0.5)))
        evidence = BeliefEvidence(
            evidence_id=inf.influence_id,
            source_type=str(inf.metadata.get("source_type", "inference")),
            support=support,
            source_ref=inf.metadata.get("source_ref"),
            reliability=reliability,
            directness=clamp01(float(inf.metadata.get("directness", 0.5))),
            at=inf.created_at,
        )
        records = []
        for b in state.records:
            if b.belief_id != belief_id:
                records.append(b)
                continue
            weight = reliability * evidence.directness
            if support == "support":
                confidence = clamp01(b.confidence + 0.15 * weight)
                stability = clamp01(b.stability + 0.05 * weight)
                status = b.status
            elif support == "contradict":
                confidence = clamp01(b.confidence - 0.25 * weight)
                stability = clamp01(b.stability - 0.05 * weight)
                status = self._status_from_confidence(b, confidence)
            else:  # qualify
                confidence = b.confidence
                stability = clamp01(b.stability + 0.02 * weight)
                status = b.status
            records.append(
                replace(
                    b, confidence=confidence, stability=stability, status=status,
                    evidence=b.evidence + (evidence,), last_updated_at=inf.created_at,
                )
            )
        return replace(state, records=tuple(records))

    def _revise(self, state: BeliefState, inf) -> BeliefState:
        belief_id = inf.metadata.get("belief_id")
        new_proposition = str(inf.metadata.get("new_proposition", ""))
        records = []
        for b in state.records:
            if b.belief_id != belief_id:
                records.append(b)
                continue
            records.append(
                replace(
                    b, proposition=new_proposition, revision=b.revision + 1,
                    history=b.history + (b.proposition,), last_updated_at=inf.created_at,
                )
            )
        return replace(state, records=tuple(records))

    def _set_status(self, state: BeliefState, inf, status: str) -> BeliefState:
        belief_id = inf.metadata.get("belief_id")
        records = tuple(
            replace(b, status=status, last_updated_at=inf.created_at)
            if b.belief_id == belief_id else b
            for b in state.records
        )
        return replace(state, records=records)

    def _activate(self, state: BeliefState, inf) -> BeliefState:
        belief_id = inf.metadata.get("belief_id")
        activation = clamp01(float(inf.metadata.get("activation", 1.0)))
        records = tuple(
            replace(b, activation=activation) if b.belief_id == belief_id else b
            for b in state.records
        )
        return replace(state, records=records)

    @staticmethod
    def _status_from_confidence(prev: BeliefRecord, confidence: float) -> str:
        if prev.status in ("SUPERSEDED", "OBSOLETE"):
            return prev.status
        if confidence < REJECTED_THRESHOLD:
            return "REJECTED"
        if confidence < WEAKENED_THRESHOLD:
            return "WEAKENED"
        return "ACTIVE"

    @staticmethod
    def _evidence_from_metadata(inf) -> tuple[BeliefEvidence, ...]:
        raw = inf.metadata.get("evidence") or ()
        evidence = []
        for i, e in enumerate(raw):
            evidence.append(
                BeliefEvidence(
                    evidence_id=f"{inf.influence_id}-ev{i + 1}",
                    source_type=str(e.get("source_type", "inference")),
                    support=e.get("support", "support"),
                    source_ref=e.get("source_ref"),
                    reliability=clamp01(float(e.get("reliability", 0.5))),
                    directness=clamp01(float(e.get("directness", 0.5))),
                    at=inf.created_at,
                )
            )
        return tuple(evidence)


def serialize(state: BeliefState) -> dict:
    return {
        "records": [
            {
                "belief_id": b.belief_id, "proposition": b.proposition,
                "confidence": b.confidence, "stability": b.stability,
                "activation": b.activation,
                "evidence": [
                    {
                        "evidence_id": e.evidence_id, "source_type": e.source_type,
                        "support": e.support, "source_ref": e.source_ref,
                        "reliability": e.reliability, "directness": e.directness,
                        "at": iso(e.at),
                    }
                    for e in b.evidence
                ],
                "status": b.status, "scope": b.scope, "belief_type": b.belief_type,
                "revision": b.revision, "history": list(b.history),
                "formed_at": iso(b.formed_at), "last_updated_at": iso(b.last_updated_at),
            }
            for b in state.records
        ],
    }


def deserialize(data: dict) -> BeliefState:
    return BeliefState(
        records=tuple(
            BeliefRecord(
                belief_id=b["belief_id"], proposition=b["proposition"],
                confidence=b["confidence"], stability=b["stability"],
                activation=b.get("activation", 0.0),
                evidence=tuple(
                    BeliefEvidence(
                        evidence_id=e["evidence_id"], source_type=e["source_type"],
                        support=e.get("support", "support"), source_ref=e.get("source_ref"),
                        reliability=e.get("reliability", 0.5),
                        directness=e.get("directness", 0.5), at=from_iso(e.get("at")),
                    )
                    for e in b.get("evidence", ())
                ),
                status=b.get("status", "ACTIVE"), scope=b.get("scope"),
                belief_type=b.get("belief_type"), revision=b.get("revision", 1),
                history=tuple(b.get("history", ())),
                formed_at=from_iso(b.get("formed_at")),
                last_updated_at=from_iso(b.get("last_updated_at")),
            )
            for b in data["records"]
        ),
    )
