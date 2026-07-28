"""Password hashing and random secret helpers.

Generic primitives with no domain knowledge — `core.auth` classes and
`base.Tokenizer` build on top of these, the same way `base.Packager` builds
on `utils.fs`.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

__hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2 (slow by design, salted per call)."""
    return __hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return __hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_password(length: int = 24) -> str:
    """URL-safe random password, used when seeding accounts on install."""
    return secrets.token_urlsafe(length)


def generate_secret(length: int = 48) -> str:
    """URL-safe random secret for opaque tokens (refresh/service tokens)."""
    return secrets.token_urlsafe(length)


def hash_secret(secret: str) -> str:
    """SHA-256 digest for storing opaque tokens at rest.

    Unlike passwords, these secrets are already high-entropy random values,
    so a fast digest is sufficient and keeps lookups by hash cheap.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
