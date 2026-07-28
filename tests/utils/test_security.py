from utils.security import (
    generate_password,
    generate_secret,
    hash_password,
    hash_secret,
    verify_password,
)


def test_hash_password_produces_argon2_hash():
    assert hash_password("correct-horse-battery-staple").startswith("$argon2")


def test_hash_password_salts_each_call():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_accepts_correct_password():
    password_hash = hash_password("correct-horse-battery-staple")
    assert verify_password(password_hash, "correct-horse-battery-staple") is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("correct-horse-battery-staple")
    assert verify_password(password_hash, "wrong-password") is False


def test_verify_password_rejects_garbage_hash():
    assert verify_password("not-a-real-hash", "anything") is False


def test_generate_password_is_unique_and_nonempty():
    first, second = generate_password(), generate_password()
    assert first != second
    assert len(first) > 0


def test_generate_secret_is_unique():
    assert generate_secret() != generate_secret()


def test_hash_secret_is_deterministic_and_one_way():
    secret = generate_secret()
    assert hash_secret(secret) == hash_secret(secret)
    assert hash_secret(secret) != secret
