"""Signed JWTs and opaque secrets from one configurable interface."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from utils import logger
from utils.security import generate_secret, hash_secret


class TokenError(Exception):
    """Raised when a token is malformed, expired, or fails verification."""


class Tokenizer:
    """One token interface: issue/decode JWTs, mint/hash opaque secrets.

    Knows nothing about users or the database — callers supply the subject
    and any extra claims. `token_type` is written into every JWT and checked
    on decode so an access token cannot be replayed as another kind.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        ttl: timedelta = timedelta(minutes=15),
        token_type: str = "access",
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.ttl = ttl
        self.token_type = token_type

    def issue(self, subject: str, ttl: timedelta = None, **claims: Any) -> str:
        """Sign a JWT for `subject`, expiring after `ttl` (default: `self.ttl`)."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "type": self.token_type,
            "iat": now,
            "exp": now + (ttl if ttl is not None else self.ttl),
            **claims,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode(self, token: str) -> dict:
        """Verify a JWT and return its claims, or raise `TokenError`."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError as exc:
            logger.warning("Token expired", token_type=self.token_type)
            raise TokenError(f"{self.token_type} token expired") from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("Token invalid", token_type=self.token_type)
            raise TokenError(f"Invalid {self.token_type} token: {exc}") from exc

        if payload.get("type") != self.token_type:
            raise TokenError(f"Not a {self.token_type} token")
        return payload

    def issue_secret(self) -> tuple[str, str]:
        """Return `(raw_secret, hash)` for an opaque token.

        The raw value is shown to its owner once; only the hash is stored.
        """
        raw = generate_secret()
        return raw, hash_secret(raw)

    def hash_secret(self, raw_secret: str) -> str:
        return hash_secret(raw_secret)

    @property
    def expiry(self) -> datetime:
        """Absolute expiry for a token issued now, at this tokenizer's TTL."""
        return datetime.now(timezone.utc) + self.ttl
