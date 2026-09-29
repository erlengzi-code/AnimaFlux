"""Identity State Owner（v5.9 §13N）。

Identity 表示 Agent 客观上的「是谁」，属于 Slow State、event-driven（§13N.14）。
Runtime Identity 与 Life Identity 分离（§13N.1）：本模块不含 agent_id / runtime_id /
branch_id 等 Runtime Metadata。chronological_age 由 birth_time + World Time 派生（§13N.3），
vital_status 权威属于 Body（§13N.4），这里都不保存。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from animaflux.contracts.state import StateResolutionResult
from animaflux.plugins.default_life._common import from_iso, iso

INFLUENCE_RENAME = "identity.rename"
INFLUENCE_ROLE_ADD = "identity.role_add"
INFLUENCE_ROLE_END = "identity.role_end"


@dataclass(frozen=True)
class Role:
    role_id: str
    role_type: str
    label: str
    status: str = "active"  # active | ended
    started_at: datetime | None = None
    ended_at: datetime | None = None
    context_ref: str | None = None
    authority: str | None = None


@dataclass(frozen=True)
class IdentityState:
    birth_time: datetime
    primary_name: str
    revision: int = 1
    aliases: tuple[str, ...] = ()
    roles: tuple[Role, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)


def validate(state: IdentityState) -> None:
    """Identity Validation 完全 deterministic（§13N.22）。"""
    if state.revision < 1:
        raise ValueError("revision must be >= 1")
    role_ids = [r.role_id for r in state.roles]
    if len(role_ids) != len(set(role_ids)):
        raise ValueError("role ids must be unique")
    for r in state.roles:
        if r.started_at and r.ended_at and r.ended_at < r.started_at:
            raise ValueError("role ended_at < started_at")


class IdentityOwner:
    """Identity 的 Primary Owner。运行期 deterministic（§13N.21）。

    Self-claim 不直接修改 Objective Identity（§13N.19）：这里只接受带权威来源的
    Transition Influence（rename / role_add / role_end）。
    """

    def resolve(self, current_state, influences, context):
        state = current_state
        changes = []
        for inf in influences:
            t = inf.influence_type
            if t == INFLUENCE_RENAME:
                new_name = inf.metadata.get("new_name")
                if new_name and new_name != state.primary_name:
                    aliases = (
                        state.aliases
                        if state.primary_name in state.aliases
                        else state.aliases + (state.primary_name,)
                    )
                    state = replace(state, primary_name=new_name, aliases=aliases)
                    changes.append(f"rename -> {new_name}")
            elif t == INFLUENCE_ROLE_ADD:
                role = inf.metadata.get("role")
                if isinstance(role, Role):
                    state = replace(state, roles=state.roles + (role,))
                    changes.append(f"role_add {role.role_id}")
            elif t == INFLUENCE_ROLE_END:
                role_id = inf.metadata.get("role_id")
                ended_at = inf.metadata.get("ended_at")
                roles = tuple(
                    replace(r, status="ended", ended_at=ended_at)
                    if r.role_id == role_id and r.status == "active" else r
                    for r in state.roles
                )
                if roles != state.roles:
                    state = replace(state, roles=roles)
                    changes.append(f"role_end {role_id}")
            # 不支持的 Influence 类型：ignore（§13A.6）
        if changes:
            state = replace(state, revision=state.revision + 1)
        validate(state)
        return StateResolutionResult(
            next_state=state, changed=(state != current_state), trace={"changes": changes},
        )

    def chronological_age(self, state: IdentityState, world_time: datetime):
        """chronological_age 派生，不持久化（§13N.3）。"""
        return world_time - state.birth_time


def serialize(state: IdentityState) -> dict:
    return {
        "birth_time": state.birth_time.isoformat(),
        "primary_name": state.primary_name,
        "revision": state.revision,
        "aliases": list(state.aliases),
        "roles": [
            {
                "role_id": r.role_id, "role_type": r.role_type, "label": r.label,
                "status": r.status, "started_at": iso(r.started_at), "ended_at": iso(r.ended_at),
                "context_ref": r.context_ref, "authority": r.authority,
            }
            for r in state.roles
        ],
        "attributes": dict(state.attributes),
    }


def deserialize(data: dict) -> IdentityState:
    return IdentityState(
        birth_time=datetime.fromisoformat(data["birth_time"]),
        primary_name=data["primary_name"],
        revision=data["revision"],
        aliases=tuple(data["aliases"]),
        roles=tuple(
            Role(
                role_id=r["role_id"], role_type=r["role_type"], label=r["label"],
                status=r.get("status", "active"),
                started_at=from_iso(r.get("started_at")), ended_at=from_iso(r.get("ended_at")),
                context_ref=r.get("context_ref"), authority=r.get("authority"),
            )
            for r in data["roles"]
        ),
        attributes=dict(data["attributes"]),
    )
