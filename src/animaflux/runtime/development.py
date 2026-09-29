"""DevelopmentContextBuilder（Cross-cutting Developmental Context §8 / §24.13）。

属于 Runtime / Integration 层：通过 Capability / Derived Index 读取 Identity / Body / Memory /
History，构造 DevelopmentContextView。不拥有长期 State（§8）。Development Context 是输入，不是
统一状态修改公式（§24.9 原则）；每个 Owner / Process 自己解释（§24.15）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from animaflux.contracts.development import DevelopmentContextView, LifeStagePolicy
from animaflux.contracts.experience import ExperienceProfileView


class HumanLifeStagePolicy:
    """官方 Human Default 参考策略（§24.5），必须可替换（§16D.28）。"""

    def stage(self, context: DevelopmentContextView) -> str:
        years = context.chronological_age.days / 365.25
        if years < 1:
            return "infancy"
        if years < 13:
            return "childhood"
        if years < 20:
            return "adolescence"
        if years < 65:
            return "adulthood"
        return "elder"


class DevelopmentContextBuilder:
    """把 Identity / Body / Experience 组装成 DevelopmentContextView（§24.8）。"""

    def __init__(self, life_stage_policy: LifeStagePolicy | None = None) -> None:
        self._life_stage_policy = life_stage_policy or HumanLifeStagePolicy()

    def build(
        self,
        *,
        agent_id: str,
        birth_time: datetime,
        runtime_time: datetime,
        biological_maturity: float = 0.5,
        domain_experience: ExperienceProfileView | None = None,
        role_refs: tuple[str, ...] = (),
        transition_refs: tuple[str, ...] = (),
    ) -> DevelopmentContextView:
        base = DevelopmentContextView(
            agent_id=agent_id,
            chronological_age=runtime_time - birth_time,
            biological_maturity=biological_maturity,
            domain_experience=domain_experience or ExperienceProfileView(),
            role_refs=tuple(role_refs),
            transition_refs=tuple(transition_refs),
        )
        # Life Stage 由可替换策略派生（§24.5），不写死在 Core（§16D.28）
        return replace(base, life_stage=self._life_stage_policy.stage(base))
