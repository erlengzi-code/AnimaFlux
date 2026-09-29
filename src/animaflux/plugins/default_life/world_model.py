"""World Model State Owner（v5.9 §13K）。

World Model = 对世界（他人 / 组织 / 事件 / 因果 / 社会规范）的主观结构认知，不是世界模拟器
（§13K.1）。它是结构性的：实体 / 关系 / 因果规则 / 规范 Schema（§13K.4），并用 belief_refs
指向支撑它的信念（§13K.5），自身不重复存储 Belief 命题。是主观的、可以出错，没有客观真值
修正（§13K.7）。LLM 不能在无证据时凭空造「事实」（§13K.22）：integration 必须携带
belief_refs / source_refs。Relation Model ≠ Relationship State：前者是「谁是上级」，后者是
「我对他的信任」（§13K.8）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_INTEGRATE = "world_model.integrate"
INFLUENCE_REVISE = "world_model.revise"

# integrate 的合法结构类型（§13K.4）
KINDS = ("entity", "relation", "causal", "schema")


@dataclass(frozen=True)
class EntityKnowledge:
    entity_ref: str
    label: str | None = None
    attributes: tuple[str, ...] = ()
    belief_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelationKnowledge:
    from_ref: str
    relation_type: str
    to_ref: str
    confidence: float = 0.5
    belief_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CausalRule:
    rule_id: str
    statement: str
    confidence: float = 0.5
    conditions: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    belief_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaKnowledge:
    schema_id: str
    name: str
    description: str = ""
    belief_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorldModelState:
    entities: tuple[EntityKnowledge, ...] = ()
    relations: tuple[RelationKnowledge, ...] = ()
    causal_rules: tuple[CausalRule, ...] = ()
    schemas: tuple[SchemaKnowledge, ...] = ()


def validate(state: WorldModelState) -> None:
    for r in state.relations:
        if not (0.0 <= r.confidence <= 1.0):
            raise ValueError(f"relation {r.from_ref}->{r.to_ref} confidence out of range")
    for c in state.causal_rules:
        if not (0.0 <= c.confidence <= 1.0):
            raise ValueError(f"causal rule {c.rule_id} confidence out of range")


class WorldModelOwner:
    """World Model 的 Primary Owner。evidence-driven 结构化集成（§13K.22）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_INTEGRATE:
                state = self._integrate(state, inf)
                changes.append(f"integrate {inf.metadata.get('kind', '?')}")
            elif t == INFLUENCE_REVISE:
                state = self._revise(state, inf)
                changes.append("revise")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _integrate(self, state: WorldModelState, inf) -> WorldModelState:
        kind = inf.metadata.get("kind")
        if kind not in KINDS:
            return state
        # 证据驱动：无 belief_refs 或 source_refs 不允许集成（§13K.22）
        belief_refs = tuple(inf.metadata.get("belief_refs") or ())
        source_refs = tuple(inf.metadata.get("source_refs") or ())
        if not belief_refs and not source_refs:
            return state
        evidence = tuple(dict.fromkeys(belief_refs + source_refs))
        if kind == "entity":
            return self._integrate_entity(state, inf, evidence)
        if kind == "relation":
            return self._integrate_relation(state, inf, evidence)
        if kind == "causal":
            return self._integrate_causal(state, inf, evidence)
        return self._integrate_schema(state, inf, evidence)

    def _integrate_entity(self, state, inf, evidence) -> WorldModelState:
        entity_ref = str(inf.metadata.get("entity_ref", ""))
        label = inf.metadata.get("label")
        attributes = tuple(inf.metadata.get("attributes") or ())
        entity = EntityKnowledge(
            entity_ref=entity_ref, label=label, attributes=attributes, belief_refs=evidence,
        )
        return replace(state, entities=state.entities + (entity,))

    def _integrate_relation(self, state, inf, evidence) -> WorldModelState:
        relation = RelationKnowledge(
            from_ref=str(inf.metadata.get("from_ref", "")),
            relation_type=str(inf.metadata.get("relation_type", "")),
            to_ref=str(inf.metadata.get("to_ref", "")),
            confidence=clamp01(float(inf.metadata.get("confidence", 0.5))),
            belief_refs=evidence,
        )
        return replace(state, relations=state.relations + (relation,))

    def _integrate_causal(self, state, inf, evidence) -> WorldModelState:
        rule = CausalRule(
            rule_id=inf.influence_id,
            statement=str(inf.metadata.get("statement", "")),
            confidence=clamp01(float(inf.metadata.get("confidence", 0.5))),
            conditions=tuple(inf.metadata.get("conditions") or ()),
            exceptions=tuple(inf.metadata.get("exceptions") or ()),
            belief_refs=evidence,
        )
        return replace(state, causal_rules=state.causal_rules + (rule,))

    def _integrate_schema(self, state, inf, evidence) -> WorldModelState:
        schema = SchemaKnowledge(
            schema_id=inf.influence_id,
            name=str(inf.metadata.get("name", "")),
            description=str(inf.metadata.get("description", "")),
            belief_refs=evidence,
        )
        return replace(state, schemas=state.schemas + (schema,))

    def _revise(self, state: WorldModelState, inf) -> WorldModelState:
        kind = inf.metadata.get("kind")
        ref = inf.metadata.get("ref")
        if kind == "relation":
            relations = []
            for r in state.relations:
                if f"{r.from_ref}->{r.to_ref}" != ref:
                    relations.append(r)
                    continue
                new_confidence = clamp01(float(inf.metadata.get("confidence", r.confidence)))
                relations.append(replace(r, confidence=new_confidence))
            return replace(state, relations=tuple(relations))
        if kind == "causal":
            rules = []
            for c in state.causal_rules:
                if c.rule_id != ref:
                    rules.append(c)
                    continue
                rules.append(
                    replace(
                        c,
                        confidence=clamp01(float(inf.metadata.get("confidence", c.confidence))),
                        exceptions=tuple(inf.metadata.get("exceptions") or c.exceptions),
                    )
                )
            return replace(state, causal_rules=tuple(rules))
        return state


def serialize(state: WorldModelState) -> dict:
    return {
        "entities": [
            {"entity_ref": e.entity_ref, "label": e.label,
             "attributes": list(e.attributes), "belief_refs": list(e.belief_refs)}
            for e in state.entities
        ],
        "relations": [
            {"from_ref": r.from_ref, "relation_type": r.relation_type, "to_ref": r.to_ref,
             "confidence": r.confidence, "belief_refs": list(r.belief_refs)}
            for r in state.relations
        ],
        "causal_rules": [
            {"rule_id": c.rule_id, "statement": c.statement, "confidence": c.confidence,
             "conditions": list(c.conditions), "exceptions": list(c.exceptions),
             "belief_refs": list(c.belief_refs)}
            for c in state.causal_rules
        ],
        "schemas": [
            {"schema_id": s.schema_id, "name": s.name, "description": s.description,
             "belief_refs": list(s.belief_refs)}
            for s in state.schemas
        ],
    }


def deserialize(data: dict) -> WorldModelState:
    return WorldModelState(
        entities=tuple(
            EntityKnowledge(
                entity_ref=e["entity_ref"], label=e.get("label"),
                attributes=tuple(e.get("attributes", ())),
                belief_refs=tuple(e.get("belief_refs", ())),
            )
            for e in data.get("entities", ())
        ),
        relations=tuple(
            RelationKnowledge(
                from_ref=r["from_ref"], relation_type=r["relation_type"], to_ref=r["to_ref"],
                confidence=r.get("confidence", 0.5), belief_refs=tuple(r.get("belief_refs", ())),
            )
            for r in data.get("relations", ())
        ),
        causal_rules=tuple(
            CausalRule(
                rule_id=c["rule_id"], statement=c.get("statement", ""),
                confidence=c.get("confidence", 0.5),
                conditions=tuple(c.get("conditions", ())),
                exceptions=tuple(c.get("exceptions", ())),
                belief_refs=tuple(c.get("belief_refs", ())),
            )
            for c in data.get("causal_rules", ())
        ),
        schemas=tuple(
            SchemaKnowledge(
                schema_id=s["schema_id"], name=s.get("name", ""),
                description=s.get("description", ""), belief_refs=tuple(s.get("belief_refs", ())),
            )
            for s in data.get("schemas", ())
        ),
    )
