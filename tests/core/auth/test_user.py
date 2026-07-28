import pytest

from core.auth.Group import Group
from core.auth.Role import Role
from core.auth.User import InvalidCredentialsError, PermissionDeniedError, User, UserError


# --- creation ---------------------------------------------------------

def test_create_hashes_the_password(db):
    user = User.create("alice", "s3cret-pass")
    assert user.password_hash != "s3cret-pass"
    assert user.verify_password("s3cret-pass") is True
    assert user.is_service is False
    assert user.is_active is True


def test_create_requires_a_password(db):
    with pytest.raises(UserError):
        User.create("alice", "")


def test_create_rejects_duplicate_username(db):
    User.create("alice", "pass")
    with pytest.raises(UserError):
        User.create("alice", "other-pass")


def test_create_attaches_groups(db):
    Group.create("Admins")
    user = User.create("alice", "pass", groups=["Admins"])
    assert list(user.groups.keys()) == ["Admins"]


def test_create_service_account_has_no_password(db):
    account = User.create_service_account("ci-bot")
    assert account.is_service is True
    assert account.password_hash is None
    assert account.verify_password("anything") is False


def test_get_returns_none_when_missing(db):
    assert User.get("ghost") is None


def test_all_returns_users_keyed_by_username(db):
    User.create("alice", "pass")
    User.create_service_account("ci-bot")
    assert sorted(User.all().keys()) == ["alice", "ci-bot"]


def test_delete_removes_the_user_and_memberships(db):
    Group.create("Admins")
    user = User.create("alice", "pass", groups=["Admins"])

    assert user.delete() is True
    assert User.get("alice") is None
    assert Group.get("Admins").members == {}


# --- passwords ------------------------------------------------------

def test_set_password_persists_the_new_hash(db):
    user = User.create("alice", "old-pass")
    user.set_password("new-pass")
    assert User.get("alice").verify_password("new-pass") is True


def test_set_password_rejects_service_accounts(db):
    account = User.create_service_account("ci-bot")
    with pytest.raises(UserError):
        account.set_password("nope")


def test_change_password_requires_the_current_one(db):
    user = User.create("alice", "old-pass")
    with pytest.raises(InvalidCredentialsError):
        user.change_password("wrong-old-pass", "new-pass")


def test_change_password_updates_the_hash(db):
    user = User.create("alice", "old-pass")
    user.change_password("old-pass", "new-pass")
    assert User.get("alice").verify_password("new-pass") is True


# --- login ------------------------------------------------------------

def test_login_returns_a_session(db):
    user = User.create("alice", "s3cret-pass")
    session = user.login("s3cret-pass")
    assert session.user.username == "alice"
    assert session.access_token and session.refresh_token


def test_login_rejects_wrong_password(db):
    user = User.create("alice", "s3cret-pass")
    with pytest.raises(InvalidCredentialsError):
        user.login("wrong-pass")


def test_login_rejects_inactive_user(db):
    user = User.create("alice", "s3cret-pass")
    user.deactivate()
    with pytest.raises(InvalidCredentialsError):
        user.login("s3cret-pass")


def test_login_rejects_service_accounts(db):
    account = User.create_service_account("ci-bot")
    with pytest.raises(InvalidCredentialsError):
        account.login("anything")


def test_authenticate_looks_up_the_user(db):
    User.create("alice", "s3cret-pass")
    assert User.authenticate("alice", "s3cret-pass").user.username == "alice"


def test_authenticate_rejects_unknown_username(db):
    with pytest.raises(InvalidCredentialsError):
        User.authenticate("ghost", "whatever")


# --- tokens -----------------------------------------------------------

def test_issue_token_mints_a_service_token(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")
    assert token.secret
    assert [t.name for t in account.tokens] == ["ci-pipeline"]


def test_issue_token_rejects_human_users(db):
    user = User.create("alice", "pass")
    with pytest.raises(UserError):
        user.issue_token("should-fail")


# --- membership and permissions --------------------------------

def test_add_to_group_is_idempotent(db):
    group = Group.create("Admins")
    user = User.create("alice", "pass")

    user.add_to_group(group)
    user.add_to_group(group)
    assert list(User.get("alice").groups.keys()) == ["Admins"]


def test_add_to_group_rejects_unknown_group(db):
    user = User.create("alice", "pass")
    with pytest.raises(UserError):
        user.add_to_group("ghost")


def test_remove_from_group_drops_membership(db):
    Group.create("Admins")
    user = User.create("alice", "pass", groups=["Admins"])

    user.remove_from_group("Admins")
    assert User.get("alice").groups == {}


def test_permissions_are_empty_without_groups(db):
    assert User.create("alice", "pass").permissions == set()


def test_permissions_come_from_the_group_role(db):
    Role.create("editor", permissions=["catalog:read", "catalog:write"])
    Group.create("Editors", role="editor")
    user = User.create("alice", "pass", groups=["Editors"])

    assert user.permissions == {"catalog:read", "catalog:write"}


def test_permissions_union_across_groups(db):
    Role.create("reader", permissions=["catalog:read"])
    Role.create("writer", permissions=["catalog:write"])
    Group.create("Readers", role="reader")
    Group.create("Writers", role="writer")

    user = User.create("alice", "pass", groups=["Readers", "Writers"])
    assert user.permissions == {"catalog:read", "catalog:write"}


def test_groups_without_a_role_contribute_nothing(db):
    Group.create("Empty")
    user = User.create("alice", "pass", groups=["Empty"])
    assert user.permissions == set()


def test_roles_lists_every_reachable_role(db):
    Role.create("reader", permissions=["catalog:read"])
    Group.create("Readers", role="reader")
    user = User.create("alice", "pass", groups=["Readers"])
    assert list(user.roles.keys()) == ["reader"]


def test_has_permission_honours_the_wildcard(db):
    Role.create("admin", permissions=[Role.WILDCARD])
    Group.create("Admins", role="admin")
    user = User.create("alice", "pass", groups=["Admins"])

    assert user.has_permission("anything:at-all") is True


def test_require_permission_passes_when_granted(db):
    Role.create("editor", permissions=["catalog:read"])
    Group.create("Editors", role="editor")
    user = User.create("alice", "pass", groups=["Editors"])

    user.require_permission("catalog:read")  # should not raise


def test_require_permission_raises_when_missing(db):
    user = User.create("alice", "pass")
    with pytest.raises(PermissionDeniedError):
        user.require_permission("catalog:write")


# --- account state ----------------------------------------------------

def test_deactivate_and_activate_persist(db):
    user = User.create("alice", "pass")

    user.deactivate()
    assert User.get("alice").is_active is False

    user.activate()
    assert User.get("alice").is_active is True


def test_set_email_persists(db):
    user = User.create("alice", "pass")
    user.set_email("alice@example.com")
    assert User.get("alice").email == "alice@example.com"
