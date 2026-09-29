"""Narrative State Owner（v5.9 §13M）。

Narrative = 关于人生「故事」的结构化自我叙事，不是 Memory 的副本（§13M.2）。结构化：
Life Themes / Turning Points / Life Chapters / Causal Interpretations / Identity Statements
/ Current Life Chapter（§13M.3）。是重构与意义赋予，不是事件流水账（§13M.1）。
Provenance：Theme / Turning Point 必须挂 source_refs（§13M.12）。Versioning：Narrative
Revision 必须版本化、可追溯（§13M.14）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import clamp01, from_iso, iso

INFLUENCE_ADD_THEME = "narrative.add_theme"
INFLUENCE_ADD_TURNING_POINT = "narrative.add_turning_point"
INFLUENCE_ADD_CHAPTER = "narrative.add_chapter"
INFLUENCE_ADD_IDENTITY_STATEMENT = "narrative.add_identity_statement"
INFLUENCE_SET_CURRENT_CHAPTER = "narrative.set_current_chapter"
INFLUENCE_REVISE = "narrative.revise"


@dataclass(frozen=True)
class LifeTheme:
    theme_id: str
    name: str
    confidence: float = 0.5
    source_refs: tuple[str, ...] = ()
    formed_at: datetime | None = None


@dataclass(frozen=True)
class TurningPoint:
    turning_point_id: str
    description: str
    importance: float = 0.5
    source_refs: tuple[str, ...] = ()
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class LifeChapter:
    chapter_id: str
    title: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    theme_refs: tuple[str, ...] = ()
    turning_point_refs: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    summary: str = ""


@dataclass(frozen=True)
class IdentityStatement:
    statement_id: str
    text: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class NarrativeState:
    themes: tuple[LifeTheme, ...] = ()
    turning_points: tuple[TurningPoint, ...] = ()
    chapters: tuple[LifeChapter, ...] = ()
    identity_statements: tuple[IdentityStatement, ...] = ()
    current_chapter_id: str | None = None
    revision: int = 1
    history: tuple[str, ...] = ()   # 每次 revise 追加一条 provenance（§13M.14）


def validate(state: NarrativeState) -> None:
    for t in state.themes:
        if not (0.0 <= t.confidence <= 1.0):
            raise ValueError(f"theme {t.theme_id} confidence out of range")
    for tp in state.turning_points:
        if not (0.0 <= tp.importance <= 1.0):
            raise ValueError(f"turning point {tp.turning_point_id} importance out of range")
    if state.revision < 1:
        raise ValueError("revision must be >= 1")


class NarrativeOwner:
    """Narrative 的 Primary Owner。结构化 + Provenance + Versioning（§13M.12 / §13M.14）。"""

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_ADD_THEME:
                state = self._add_theme(state, inf)
                changes.append("add_theme")
            elif t == INFLUENCE_ADD_TURNING_POINT:
                state = self._add_turning_point(state, inf)
                changes.append("add_turning_point")
            elif t == INFLUENCE_ADD_CHAPTER:
                state = self._add_chapter(state, inf)
                changes.append("add_chapter")
            elif t == INFLUENCE_ADD_IDENTITY_STATEMENT:
                state = self._add_identity_statement(state, inf)
                changes.append("add_identity_statement")
            elif t == INFLUENCE_SET_CURRENT_CHAPTER:
                state = self._set_current_chapter(state, inf)
                changes.append("set_current_chapter")
            elif t == INFLUENCE_REVISE:
                state = self._revise(state, inf)
                changes.append(f"revise -> {state.revision}")
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def _add_theme(self, state: NarrativeState, inf) -> NarrativeState:
        source_refs = tuple(inf.metadata.get("source_refs") or ())
        # Provenance：无 source_refs 不落 Theme（§13M.12）
        if not source_refs:
            return state
        theme = LifeTheme(
            theme_id=inf.influence_id, name=str(inf.metadata.get("name", "")),
            confidence=clamp01(float(inf.metadata.get("confidence", 0.5))),
            source_refs=source_refs, formed_at=inf.created_at,
        )
        return replace(state, themes=state.themes + (theme,))

    def _add_turning_point(self, state: NarrativeState, inf) -> NarrativeState:
        source_refs = tuple(inf.metadata.get("source_refs") or ())
        # Turning Point 必须可回溯到具体事件（§13M.12）
        if not source_refs:
            return state
        tp = TurningPoint(
            turning_point_id=inf.influence_id,
            description=str(inf.metadata.get("description", "")),
            importance=clamp01(float(inf.metadata.get("importance", 0.5))),
            source_refs=source_refs, occurred_at=inf.created_at,
        )
        return replace(state, turning_points=state.turning_points + (tp,))

    def _add_chapter(self, state: NarrativeState, inf) -> NarrativeState:
        chapter = LifeChapter(
            chapter_id=inf.influence_id, title=str(inf.metadata.get("title", "")),
            start_time=inf.metadata.get("start_time") or inf.created_at,
            end_time=inf.metadata.get("end_time"),
            theme_refs=tuple(inf.metadata.get("theme_refs") or ()),
            turning_point_refs=tuple(inf.metadata.get("turning_point_refs") or ()),
            memory_refs=tuple(inf.metadata.get("memory_refs") or ()),
            summary=str(inf.metadata.get("summary", "")),
        )
        return replace(state, chapters=state.chapters + (chapter,))

    def _add_identity_statement(self, state: NarrativeState, inf) -> NarrativeState:
        stmt = IdentityStatement(
            statement_id=inf.influence_id, text=str(inf.metadata.get("text", "")),
            source_refs=tuple(inf.metadata.get("source_refs") or ()),
        )
        return replace(state, identity_statements=state.identity_statements + (stmt,))

    def _set_current_chapter(self, state: NarrativeState, inf) -> NarrativeState:
        chapter_id = inf.metadata.get("chapter_id")
        if chapter_id is None:
            return state
        return replace(state, current_chapter_id=str(chapter_id))

    def _revise(self, state: NarrativeState, inf) -> NarrativeState:
        note = str(inf.metadata.get("note", "revision"))
        record = f"r{state.revision}: {note}"
        return replace(state, revision=state.revision + 1, history=state.history + (record,))


def serialize(state: NarrativeState) -> dict:
    return {
        "themes": [
            {"theme_id": t.theme_id, "name": t.name, "confidence": t.confidence,
             "source_refs": list(t.source_refs), "formed_at": iso(t.formed_at)}
            for t in state.themes
        ],
        "turning_points": [
            {"turning_point_id": tp.turning_point_id, "description": tp.description,
             "importance": tp.importance, "source_refs": list(tp.source_refs),
             "occurred_at": iso(tp.occurred_at)}
            for tp in state.turning_points
        ],
        "chapters": [
            {"chapter_id": c.chapter_id, "title": c.title, "start_time": iso(c.start_time),
             "end_time": iso(c.end_time), "theme_refs": list(c.theme_refs),
             "turning_point_refs": list(c.turning_point_refs), "memory_refs": list(c.memory_refs),
             "summary": c.summary}
            for c in state.chapters
        ],
        "identity_statements": [
            {"statement_id": s.statement_id, "text": s.text, "source_refs": list(s.source_refs)}
            for s in state.identity_statements
        ],
        "current_chapter_id": state.current_chapter_id,
        "revision": state.revision,
        "history": list(state.history),
    }


def deserialize(data: dict) -> NarrativeState:
    return NarrativeState(
        themes=tuple(
            LifeTheme(theme_id=t["theme_id"], name=t.get("name", ""),
                      confidence=t.get("confidence", 0.5),
                      source_refs=tuple(t.get("source_refs", ())),
                      formed_at=from_iso(t.get("formed_at")))
            for t in data.get("themes", ())
        ),
        turning_points=tuple(
            TurningPoint(turning_point_id=tp["turning_point_id"],
                         description=tp.get("description", ""),
                         importance=tp.get("importance", 0.5),
                         source_refs=tuple(tp.get("source_refs", ())),
                         occurred_at=from_iso(tp.get("occurred_at")))
            for tp in data.get("turning_points", ())
        ),
        chapters=tuple(
            LifeChapter(chapter_id=c["chapter_id"], title=c.get("title", ""),
                        start_time=from_iso(c.get("start_time")),
                        end_time=from_iso(c.get("end_time")),
                        theme_refs=tuple(c.get("theme_refs", ())),
                        turning_point_refs=tuple(c.get("turning_point_refs", ())),
                        memory_refs=tuple(c.get("memory_refs", ())),
                        summary=c.get("summary", ""))
            for c in data.get("chapters", ())
        ),
        identity_statements=tuple(
            IdentityStatement(statement_id=s["statement_id"], text=s.get("text", ""),
                              source_refs=tuple(s.get("source_refs", ())))
            for s in data.get("identity_statements", ())
        ),
        current_chapter_id=data.get("current_chapter_id"),
        revision=data.get("revision", 1),
        history=tuple(data.get("history", ())),
    )
