"""Default Life 插件：13 个 Core State 的确定性 Owner + 序列化。

P5 最小生命切片（Identity / Body / Emotion）+ P8 动机与社会认知（Drive / Belief / Goal /
Relationship）+ P9 慢速自我发展（Personality / Value / World Model / Self Model / Narrative）。
"""

from __future__ import annotations

from animaflux.contracts.state import StateNamespace
from animaflux.plugins.default_life import (
    belief,
    body,
    drive,
    emotion,
    goal,
    identity,
    narrative,
    personality,
    relationship,
    self_model,
    value,
    world_model,
)
from animaflux.plugins.default_life.belief import BeliefOwner, BeliefState
from animaflux.plugins.default_life.body import BodyOwner, BodyState
from animaflux.plugins.default_life.drive import DriveOwner, DriveState
from animaflux.plugins.default_life.emotion import EmotionOwner, EmotionState
from animaflux.plugins.default_life.goal import GoalOwner, GoalState
from animaflux.plugins.default_life.identity import IdentityOwner, IdentityState
from animaflux.plugins.default_life.narrative import NarrativeOwner, NarrativeState
from animaflux.plugins.default_life.personality import PersonalityOwner, PersonalityState
from animaflux.plugins.default_life.relationship import RelationshipOwner, RelationshipState
from animaflux.plugins.default_life.self_model import SelfModelOwner, SelfModelState
from animaflux.plugins.default_life.value import ValueOwner, ValueState
from animaflux.plugins.default_life.world_model import WorldModelOwner, WorldModelState

__all__ = [
    "BeliefOwner",
    "BeliefState",
    "BodyOwner",
    "BodyState",
    "DriveOwner",
    "DriveState",
    "EmotionOwner",
    "EmotionState",
    "GoalOwner",
    "GoalState",
    "IdentityOwner",
    "IdentityState",
    "NarrativeOwner",
    "NarrativeState",
    "PersonalityOwner",
    "PersonalityState",
    "RelationshipOwner",
    "RelationshipState",
    "SelfModelOwner",
    "SelfModelState",
    "ValueOwner",
    "ValueState",
    "WorldModelOwner",
    "WorldModelState",
    "register_default_life",
]


def register_default_life(runtime) -> None:
    """把全部 Default Life Owner 装配进 LifeRuntime（§16C.18 Plugin Selection 外部化）。"""
    runtime.register_owner(
        StateNamespace.IDENTITY, IdentityOwner(), serialize=identity.serialize, validate=identity.validate
    )
    runtime.register_owner(
        StateNamespace.BODY, BodyOwner(), serialize=body.serialize, validate=body.validate
    )
    runtime.register_owner(
        StateNamespace.EMOTION, EmotionOwner(), serialize=emotion.serialize, validate=emotion.validate
    )
    runtime.register_owner(
        StateNamespace.DRIVE, DriveOwner(), serialize=drive.serialize, validate=drive.validate
    )
    runtime.register_owner(
        StateNamespace.BELIEF, BeliefOwner(), serialize=belief.serialize, validate=belief.validate
    )
    runtime.register_owner(
        StateNamespace.GOAL, GoalOwner(), serialize=goal.serialize, validate=goal.validate
    )
    runtime.register_owner(
        StateNamespace.RELATIONSHIP, RelationshipOwner(),
        serialize=relationship.serialize, validate=relationship.validate,
    )
    runtime.register_owner(
        StateNamespace.PERSONALITY, PersonalityOwner(),
        serialize=personality.serialize, validate=personality.validate,
    )
    runtime.register_owner(
        StateNamespace.VALUE, ValueOwner(), serialize=value.serialize, validate=value.validate
    )
    runtime.register_owner(
        StateNamespace.WORLD_MODEL, WorldModelOwner(),
        serialize=world_model.serialize, validate=world_model.validate,
    )
    runtime.register_owner(
        StateNamespace.SELF_MODEL, SelfModelOwner(),
        serialize=self_model.serialize, validate=self_model.validate,
    )
    runtime.register_owner(
        StateNamespace.NARRATIVE, NarrativeOwner(),
        serialize=narrative.serialize, validate=narrative.validate,
    )
