from datetime import timedelta

import pytest

from app.base.Tokenizer import TokenError
from app.core.auth.ServiceToken import ServiceToken
from app.core.auth.User import User, UserError
from utils.helpers import utcnow


def test_issue_returns_the_secret_once(db):
    account = User.create_service_account("ci-bot")
    token = ServiceToken.issue(account, "ci-pipeline")

    assert token.secret
    assert ServiceToken.get(account, "ci-pipeline").secret is None


def test_issue_rejects_human_users(db):
    user = User.create("alice", "pass")
    with pytest.raises(UserError):
        ServiceToken.issue(user, "should-fail")


def test_authenticate_returns_the_service_account(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")

    assert ServiceToken.authenticate(token.secret).username == "ci-bot"


def test_authenticate_records_last_used(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")

    ServiceToken.authenticate(token.secret)
    assert ServiceToken.get(account, "ci-pipeline").last_used_at is not None


def test_authenticate_rejects_an_unknown_token(db):
    with pytest.raises(TokenError):
        ServiceToken.authenticate("not-a-real-token")


def test_authenticate_rejects_an_expired_token(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline", expires_at=utcnow() - timedelta(seconds=1))

    with pytest.raises(TokenError):
        ServiceToken.authenticate(token.secret)


def test_authenticate_rejects_a_deactivated_account(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")
    account.deactivate()

    with pytest.raises(TokenError):
        ServiceToken.authenticate(token.secret)


def test_revoke_invalidates_the_token(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")

    token.revoke()
    assert token.is_active is False
    with pytest.raises(TokenError):
        ServiceToken.authenticate(token.secret)


def test_revoke_twice_is_a_noop(db):
    token = User.create_service_account("ci-bot").issue_token("ci-pipeline")
    token.revoke()
    token.revoke()  # should not raise


def test_all_for_lists_every_token(db):
    account = User.create_service_account("ci-bot")
    account.issue_token("ci-pipeline")
    account.issue_token("nightly-job")

    assert sorted(token.name for token in ServiceToken.all_for(account)) == [
        "ci-pipeline",
        "nightly-job",
    ]


def test_is_active_reflects_expiry(db):
    account = User.create_service_account("ci-bot")
    live = account.issue_token("live", expires_at=utcnow() + timedelta(days=1))
    expired = account.issue_token("expired", expires_at=utcnow() - timedelta(days=1))

    assert live.is_active is True
    assert expired.is_active is False


def test_info_does_not_leak_the_secret(db):
    token = User.create_service_account("ci-bot").issue_token("ci-pipeline")
    assert token.secret not in token.info


def test_delete_removes_the_token(db):
    account = User.create_service_account("ci-bot")
    token = account.issue_token("ci-pipeline")

    assert token.delete() is True
    assert ServiceToken.all_for(account) == []
