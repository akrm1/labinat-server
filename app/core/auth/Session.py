"""Human user session: a JWT access token plus a rotatable refresh token."""

from __future__ import annotations

from datetime import timedelta

from app.base.Tokenizer import Tokenizer, TokenError
from app.core.auth.User import User
from data.database import get_db
from data.models.RefreshTokenModel import RefreshTokenModel
from utils import logger
from utils.helpers import asjson, generate_unique_id, utcnow
from utils.security import generate_secret


class Session:
    """One logged-in session, issued by `User.login`.

    The access token is a short-lived signed JWT sent with every request.
    The refresh token is an opaque secret, stored only as a hash, and
    rotated on each `refresh()` so a captured one cannot be reused.

    Signing is configured once at startup from `auth.token` in `config.yaml`
    (see `bootstrap.init`); until then a random per-process secret is used so
    tests and scripts still work.
    """

    __tokenizer: Tokenizer = None
    __refresh_ttl: timedelta = timedelta(days=30)

    def __init__(self, user: User, access_token: str, refresh_token: str, expires_in: int):
        self.__user: User = user
        self.__access_token: str = access_token
        self.__refresh_token: str = refresh_token
        self.__expires_in: int = expires_in
        logger.debug("Session constructed", username=user.username, expires_in=expires_in)

    @classmethod
    def init(cls, secret: str, algorithm: str, access_ttl_minutes: int, refresh_ttl_days: int) -> None:
        """Wire token signing from `auth.token`.

        `secret` is expected to be already resolved (`bootstrap` reads it
        from `secret-path`, generating the file on first run). Without one, an
        ephemeral secret is used and every restart invalidates old tokens.
        """
        cls.__tokenizer = Tokenizer(
            secret=secret,
            algorithm=algorithm,
            ttl=timedelta(minutes=access_ttl_minutes),
            token_type="access",
        )
        cls.__refresh_ttl = timedelta(days=refresh_ttl_days)
        logger.debug(
            "Session signing configured",
            algorithm=cls.__tokenizer.algorithm,
            access_ttl=str(cls.__tokenizer.ttl),
            refresh_ttl=str(cls.__refresh_ttl),
        )

    @classmethod
    def tokenizer(cls) -> Tokenizer:
        """The configured tokenizer, falling back to an ephemeral secret."""
        if cls.__tokenizer is None:
            logger.warning("Session signing not configured; using an ephemeral secret")
            cls.init(generate_secret(), "HS256", 15, 30)
        return cls.__tokenizer

    @classmethod
    def issue(cls, user: User) -> "Session":
        """Open a new session for `user` (called by `User.login`)."""
        tokenizer = cls.tokenizer()
        access_token = tokenizer.issue(user.id, username=user.username)
        refresh_token, refresh_hash = tokenizer.issue_secret()

        with get_db() as db:
            db.add(RefreshTokenModel(
                id=generate_unique_id(),
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=utcnow() + cls.__refresh_ttl,
            ))
            db.commit()

        logger.info("Session issued", username=user.username)
        return cls(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(tokenizer.ttl.total_seconds()),
        )

    @classmethod
    def refresh(cls, refresh_token: str) -> "Session":
        """Rotate a refresh token: revoke the old one, issue a fresh session."""
        token_hash = cls.tokenizer().hash_secret(refresh_token)

        with get_db() as db:
            record = db.query(RefreshTokenModel).filter_by(token_hash=token_hash).first()
            if not record or record.revoked_at is not None:
                logger.warning("Refresh rejected: token invalid or revoked")
                raise TokenError("Refresh token is invalid or revoked")
            if record.expires_at <= utcnow():
                logger.warning("Refresh rejected: token expired")
                raise TokenError("Refresh token expired")

            record.revoked_at = utcnow()
            user_id = record.user_id
            db.commit()

        user = cls.__active_user(user_id)
        logger.info("Session refreshed", username=user.username)
        return cls.issue(user)

    @classmethod
    def revoke(cls, refresh_token: str) -> None:
        """Log out: invalidate a refresh token (no-op if already revoked)."""
        token_hash = cls.tokenizer().hash_secret(refresh_token)

        with get_db() as db:
            record = db.query(RefreshTokenModel).filter_by(token_hash=token_hash).first()
            if not record or record.revoked_at is not None:
                return
            record.revoked_at = utcnow()
            db.commit()

        logger.info("Session revoked")

    @classmethod
    def revoke_all(cls, user: User) -> int:
        """Invalidate every live session for `user`. Returns how many."""
        with get_db() as db:
            records = db.query(RefreshTokenModel).filter_by(
                user_id=user.id, revoked_at=None
            ).all()
            for record in records:
                record.revoked_at = utcnow()
            db.commit()

        logger.info("All sessions revoked", username=user.username, sessions=len(records))
        return len(records)

    @classmethod
    def authenticate(cls, access_token: str) -> User:
        """Verify an access token and return the user it belongs to."""
        payload = cls.tokenizer().decode(access_token)
        return cls.__active_user(payload["sub"])

    @classmethod
    def __active_user(cls, user_id: str) -> User:
        user = User.get_by_id(user_id)
        if user is None:
            raise TokenError("Token refers to a user that no longer exists")
        if not user.is_active:
            logger.warning("Token rejected for inactive user", username=user.username)
            raise TokenError(f"User '{user.username}' is inactive")
        return user

    @property
    def user(self) -> User:
        return self.__user

    @property
    def access_token(self) -> str:
        return self.__access_token

    @property
    def refresh_token(self) -> str:
        return self.__refresh_token

    @property
    def expires_in(self) -> int:
        """Access token lifetime in seconds."""
        return self.__expires_in

    @property
    def token_type(self) -> str:
        return "bearer"

    def astokens(self) -> dict:
        """Token payload for an HTTP response (includes the raw secrets)."""
        return {
            "access_token": self.__access_token,
            "refresh_token": self.__refresh_token,
            "token_type": self.token_type,
            "expires_in": self.__expires_in,
        }

    @property
    def info(self):
        """Session description. Deliberately omits the tokens themselves."""
        return asjson({
            "user": self.__user.username,
            "token_type": self.token_type,
            "expires_in": self.__expires_in,
        })

    def __str__(self):
        return self.info

    def __repr__(self):
        return f"Session({self.__user.username})"
