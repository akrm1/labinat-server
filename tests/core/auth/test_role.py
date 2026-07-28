import pytest

from core.auth.Group import Group
from core.auth.Role import Role, RoleError


def test_create_persists_permissions(db):
    role = Role.create("editor", permissions=["catalog:read"])
    assert role.permissions == ["catalog:read"]
    assert Role.get("editor").id == role.id


def test_create_rejects_duplicate_name(db):
    Role.create("editor")
    with pytest.raises(RoleError):
        Role.create("editor")


def test_get_returns_none_when_missing(db):
    assert Role.get("ghost") is None


def test_get_or_create_is_idempotent(db):
    first = Role.get_or_create("admin", permissions=["*"])
    second = Role.get_or_create("admin", permissions=["should-be-ignored"])
    assert first.id == second.id
    assert second.permissions == ["*"]


def test_all_returns_roles_keyed_by_name(db):
    Role.create("editor")
    Role.create("viewer")
    assert sorted(Role.all().keys()) == ["editor", "viewer"]


def test_grant_adds_permission_and_persists(db):
    role = Role.create("editor")
    role.grant("catalog:write")
    assert Role.get("editor").permissions == ["catalog:write"]


def test_grant_is_idempotent(db):
    role = Role.create("editor", permissions=["catalog:write"])
    role.grant("catalog:write")
    assert role.permissions == ["catalog:write"]


def test_revoke_removes_permission_and_persists(db):
    role = Role.create("editor", permissions=["catalog:read", "catalog:write"])
    role.revoke("catalog:write")
    assert Role.get("editor").permissions == ["catalog:read"]


def test_revoke_unknown_permission_is_a_noop(db):
    role = Role.create("editor", permissions=["catalog:read"])
    role.revoke("never-granted")
    assert role.permissions == ["catalog:read"]


def test_set_permissions_replaces_the_list(db):
    role = Role.create("editor", permissions=["catalog:read"])
    role.set_permissions(["workspace:write"])
    assert Role.get("editor").permissions == ["workspace:write"]


def test_has_permission_matches_granted_only(db):
    role = Role.create("editor", permissions=["catalog:read"])
    assert role.has_permission("catalog:read") is True
    assert role.has_permission("catalog:write") is False


def test_wildcard_grants_everything(db):
    role = Role.create("admin", permissions=[Role.WILDCARD])
    assert role.has_permission("anything:at-all") is True


def test_delete_removes_unused_role(db):
    Role.create("editor").delete()
    assert Role.get("editor") is None


def test_delete_rejects_role_still_bound_to_a_group(db):
    role = Role.create("admin", permissions=["*"])
    Group.create("Admins", role=role)
    with pytest.raises(RoleError):
        role.delete()
