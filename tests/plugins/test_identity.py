"""P5 Identity Owner 测试（§13N：rename / role / revision / chronological_age）。"""

from datetime import datetime, timedelta

import pytest

from animaflux.contracts.influence import Influence
from animaflux.plugins.default_life.identity import (
    INFLUENCE_RENAME,
    INFLUENCE_ROLE_ADD,
    INFLUENCE_ROLE_END,
    IdentityOwner,
    IdentityState,
    Role,
    validate,
)

T0 = datetime(2000, 1, 1)


def _inf(influence_type: str, metadata: dict | None = None) -> Influence:
    return Influence(
        influence_id="INF-1",
        source_plugin="test",
        target_state="identity",
        influence_type=influence_type,
        magnitude=0.0,
        created_at=T0,
        metadata=metadata or {},
    )


def test_rename_changes_name_aliases_and_revision():
    owner = IdentityOwner()
    state = IdentityState(birth_time=T0, primary_name="旧名")
    out = owner.resolve(state, [_inf(INFLUENCE_RENAME, {"new_name": "新名"})], None)
    assert out.next_state.primary_name == "新名"
    assert "旧名" in out.next_state.aliases
    assert out.next_state.revision == 2
    assert out.changed is True


def test_rename_to_same_name_is_noop():
    owner = IdentityOwner()
    state = IdentityState(birth_time=T0, primary_name="同名")
    out = owner.resolve(state, [_inf(INFLUENCE_RENAME, {"new_name": "同名"})], None)
    assert out.changed is False


def test_role_add_and_end():
    owner = IdentityOwner()
    state = IdentityState(birth_time=T0, primary_name="A")
    role = Role(role_id="r1", role_type="job", label="医生", started_at=T0)
    out = owner.resolve(state, [_inf(INFLUENCE_ROLE_ADD, {"role": role})], None)
    assert out.next_state.roles == (role,)
    out2 = owner.resolve(
        out.next_state,
        [_inf(INFLUENCE_ROLE_END, {"role_id": "r1", "ended_at": T0 + timedelta(days=1)})],
        None,
    )
    assert out2.next_state.roles[0].status == "ended"


def test_chronological_age_derived_not_persisted():
    owner = IdentityOwner()
    state = IdentityState(birth_time=T0, primary_name="A")
    assert owner.chronological_age(state, T0 + timedelta(days=365)) == timedelta(days=365)


def test_validate_rejects_duplicate_role_ids():
    state = IdentityState(
        birth_time=T0,
        primary_name="A",
        roles=(Role(role_id="r1", role_type="x", label="a"), Role(role_id="r1", role_type="y", label="b")),
    )
    with pytest.raises(ValueError):
        validate(state)
