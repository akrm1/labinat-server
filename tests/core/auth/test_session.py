import pytest

from base.Tokenizer import TokenError
from core.auth.Session import Session
from core.auth.User import User


@pytest.fixture(autouse=True)
def signing_config():
    Session.init("test-secret-value", "HS256", 15, 30)


def test_issue_returns_both_tokens(db):
    user = User.create("alice", "pass")
    session = Session.issue(user)

    assert session.access_token and session.refresh_token
    assert session.token_type == "bearer"
    assert session.expires_in == 15 * 60


def test_astokens_carries_the_payload_for_a_response(db):
    session = User.create("alice", "pass").login("pass")
    payload = session.astokens()
    assert payload["access_token"] == session.access_token
    assert payload["refresh_token"] == session.refresh_token
    assert payload["token_type"] == "bearer"


def test_info_does_not_leak_tokens(db):
    session = User.create("alice", "pass").login("pass")
    assert session.access_token not in session.info
    assert session.refresh_token not in session.info


def test_authenticate_returns_the_user(db):
    session = User.create("alice", "pass").login("pass")
    assert Session.authenticate(session.access_token).username == "alice"


def test_authenticate_rejects_a_garbage_token(db):
    with pytest.raises(TokenError):
        Session.authenticate("not-a-real-token")


def test_authenticate_rejects_a_deactivated_user(db):
    user = User.create("alice", "pass")
    session = user.login("pass")
    user.deactivate()

    with pytest.raises(TokenError):
        Session.authenticate(session.access_token)


def test_refresh_rotates_the_token_pair(db):
    session = User.create("alice", "pass").login("pass")
    refreshed = Session.refresh(session.refresh_token)

    assert refreshed.user.username == "alice"
    assert refreshed.refresh_token != session.refresh_token


def test_refresh_consumes_the_old_token(db):
    session = User.create("alice", "pass").login("pass")
    Session.refresh(session.refresh_token)

    with pytest.raises(TokenError):
        Session.refresh(session.refresh_token)


def test_refresh_rejects_an_unknown_token(db):
    with pytest.raises(TokenError):
        Session.refresh("not-a-real-token")


def test_refresh_rejects_a_deactivated_user(db):
    user = User.create("alice", "pass")
    session = user.login("pass")
    user.deactivate()

    with pytest.raises(TokenError):
        Session.refresh(session.refresh_token)


def test_revoke_invalidates_the_refresh_token(db):
    session = User.create("alice", "pass").login("pass")
    Session.revoke(session.refresh_token)

    with pytest.raises(TokenError):
        Session.refresh(session.refresh_token)


def test_revoke_is_a_noop_for_unknown_tokens(db):
    Session.revoke("not-a-real-token")  # should not raise


def test_revoke_all_kills_every_live_session(db):
    user = User.create("alice", "pass")
    first = user.login("pass")
    second = user.login("pass")

    assert Session.revoke_all(user) == 2
    for session in (first, second):
        with pytest.raises(TokenError):
            Session.refresh(session.refresh_token)


def test_tokens_from_another_secret_are_rejected(db):
    session = User.create("alice", "pass").login("pass")
    Session.init("a-completely-different-secret", "HS256", 15, 30)

    with pytest.raises(TokenError):
        Session.authenticate(session.access_token)
