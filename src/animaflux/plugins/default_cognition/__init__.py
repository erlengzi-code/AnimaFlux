"""Default Cognition 插件：Perception / Appraisal / Decision / Communication / Reflection。

P6 认知切片（Perception / Appraisal）+ P8 决策与交流（Decision / Communication）+ P9 反思
（Reflection）。Memory Retrieval 位于 memory 包。
"""

from __future__ import annotations

from animaflux.plugins.default_cognition.appraisal import (
    AppraisalProcess,
    derive_emotion_influences,
)
from animaflux.plugins.default_cognition.communication import CommunicationProcess
from animaflux.plugins.default_cognition.decision import DecisionProcess, make_candidate
from animaflux.plugins.default_cognition.perception import PerceptionProcess
from animaflux.plugins.default_cognition.reflection import (
    EvidenceItem,
    ReflectionProcess,
)
from animaflux.plugins.default_cognition.slow_development import (
    derive_slow_influences,
    evidence_item_for_appraisal,
)

__all__ = [
    "AppraisalProcess",
    "CommunicationProcess",
    "DecisionProcess",
    "EvidenceItem",
    "PerceptionProcess",
    "ReflectionProcess",
    "derive_emotion_influences",
    "derive_slow_influences",
    "evidence_item_for_appraisal",
    "make_candidate",
]
