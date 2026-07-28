from datetime import timedelta

import jwt
import pytest

from base.Tokenizer import Tokenizer, TokenError


def make_tokenizer(**kwargs):
    return Tokenizer(secret="test-secret-value", **kwargs)


def test_issue_round_trips_through_decode():
    tokenizer = make_tokenizer()
    payload = tokenizer.decode(tokenizer.issue("user-1"))
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"


def test_issue_carries_extra_claims():
    tokenizer = make_tokenizer()
    payload = tokenizer.decode(tokenizer.issue("user-1", username="lab-admin"))
    assert payload["username"] == "lab-admin"


def test_decode_rejects_token_signed_with_another_secret():
    token = Tokenizer(secret="one-secret").issue("user-1")
    with pytest.raises(TokenError):
        Tokenizer(secret="another-secret").decode(token)


def test_decode_rejects_expired_token():
    tokenizer = make_tokenizer()
    token = tokenizer.issue("user-1", ttl=timedelta(seconds=-1))
    with pytest.raises(TokenError):
        tokenizer.decode(token)


def test_per_call_ttl_overrides_the_default():
    tokenizer = make_tokenizer(ttl=timedelta(seconds=-1))
    token = tokenizer.issue("user-1", ttl=timedelta(minutes=5))
    assert tokenizer.decode(token)["sub"] == "user-1"


def test_decode_rejects_a_different_token_type():
    token = jwt.encode({"sub": "user-1", "type": "refresh"}, "test-secret-value", algorithm="HS256")
    with pytest.raises(TokenError):
        make_tokenizer().decode(token)


def test_token_type_is_configurable():
    tokenizer = make_tokenizer(token_type="invite")
    assert tokenizer.decode(tokenizer.issue("user-1"))["type"] == "invite"


def test_issue_secret_returns_raw_and_matching_hash():
    tokenizer = make_tokenizer()
    raw, hashed = tokenizer.issue_secret()
    assert raw != hashed
    assert tokenizer.hash_secret(raw) == hashed


def test_issue_secret_is_unique_per_call():
    tokenizer = make_tokenizer()
    assert tokenizer.issue_secret()[0] != tokenizer.issue_secret()[0]
