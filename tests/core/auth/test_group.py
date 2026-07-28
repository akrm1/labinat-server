import pytest

from core.auth.Group import Group, GroupError
from core.auth.Role import Role
from core.auth.User import User


def test_create_binds_role_instance(db):
    role = Role.create("admin", permissions=["*"])
    group = Group.create("Admins", role=role)
    assert group.role.id == role.id
    assert Group.get("Admins").role.name == "admin"


def test_create_accepts_role_name(db):
    Role.create("admin", permissions=["*"])
    assert Group.create("Admins", role="admin").role.name == "admin"


def test_create_without_role_grants_nothing(db):
    group = Group.create("Empty")
    assert group.role is None
    assert group.permissions == []


def test_create_rejects_duplicate_name(db):
    Group.create("Admins")
    with pytest.raises(GroupError):
        Group.create("Admins")


def test_create_rejects_unknown_role_name(db):
    with pytest.raises(GroupError):
        Group.create("Admins", role="ghost")


def test_get_returns_none_when_missing(db):
    assert Group.get("ghost") is None


def test_get_or_create_is_idempotent(db):
    first = Group.get_or_create("Admins")
    assert Group.get_or_create("Admins").id == first.id


def test_all_returns_groups_keyed_by_name(db):
    Group.create("Admins")
    Group.create("Editors")
    assert sorted(Group.all().keys()) == ["Admins", "Editors"]


def test_set_role_rebinds_and_persists(db):
    Role.create("admin", permissions=["*"])
    group = Group.create("Admins")
    group.set_role("admin")
    assert Group.get("Admins").role.name == "admin"


def test_set_role_none_clears_the_binding(db):
    role = Role.create("admin", permissions=["*"])
    group = Group.create("Admins", role=role)
    group.set_role(None)
    assert Group.get("Admins").role is None


def test_permissions_come_from_the_bound_role(db):
    Role.create("editor", permissions=["catalog:read"])
    group = Group.create("Editors", role="editor")
    assert group.permissions == ["catalog:read"]
    assert group.has_permission("catalog:read") is True


def test_members_lists_users_in_the_group(db):
    group = Group.create("Admins")
    user = User.create("alice", "pass")
    user.add_to_group(group)
    assert list(group.members.keys()) == ["alice"]


def test_add_and_remove_member_delegate_to_user(db):
    group = Group.create("Admins")
    user = User.create("alice", "pass")

    group.add_member(user)
    assert "alice" in group.members

    group.remove_member(user)
    assert group.members == {}


def test_delete_removes_group_and_memberships(db):
    group = Group.create("Admins")
    user = User.create("alice", "pass")
    user.add_to_group(group)

    assert group.delete() is True
    assert Group.get("Admins") is None
    assert User.get("alice").groups == {}
