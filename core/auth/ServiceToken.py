"""Service account API token: a long-lived opaque bearer token."""

from __future__ import annotations

from datetime import datetime
from typing import Union

from base.Tokenizer import TokenError
from core.auth.User import User, UserError
from data.database import get_db
from data.models.ServiceTokenModel import ServiceTokenModel
from utils import logger
from utils.helpers import asjson, generate_unique_id, utcnow
from utils.security import generate_secret, hash_secret


class ServiceToken:
    """How external software authenticates against the server.

    Issued only to service accounts (`User.is_service`), since human users
    log in with a password instead. The raw secret exists once — on the
    object returned by `issue()` — and only its hash is stored, so a lost
    token is replaced rather than recovered.
    """

    def __init__(
        self,
        id: str,
        user_id: str,
        name: str,
        expires_at: datetime = None,
        revoked_at: datetime = None,
        last_used_at: datetime = None,
        secret: str = None,
    ):
        self.__id: str = id
        self.__user_id: str = user_id
        self.__name: str = name
        self.__expires_at: datetime = expires_at
        self.__revoked_at: datetime = revoked_at
        self.__last_used_at: datetime = last_used_at
        self.__secret: str = secret
        logger.debug("ServiceToken constructed", token=name, user_id=user_id)

    @classmethod
    def __from_record(cls, record: ServiceTokenModel) -> "ServiceToken":
        return cls(
            id=record.id,
            user_id=record.user_id,
            name=record.name,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            last_used_at=record.last_used_at,
        )

    @classmethod
    def issue(cls, user: User, name: str, expires_at: datetime = None) -> "ServiceToken":
        """Mint a token for a service account. Read `secret` before discarding."""
        if not user.is_service:
            raise UserError(
                f"Service tokens are only issued to service accounts: {user.username}"
            )

        secret = generate_secret()
        token_id = generate_unique_id()

        with get_db() as db:
            db.add(ServiceTokenModel(
                id=token_id,
                user_id=user.id,
                name=name,
                token_hash=hash_secret(secret),
                expires_at=expires_at,
            ))
            db.commit()

        logger.info("Service token issued", username=user.username, token=name)
        return cls(
            id=token_id,
            user_id=user.id,
            name=name,
            expires_at=expires_at,
            secret=secret,
        )

    @classmethod
    def authenticate(cls, secret: str) -> User:
        """Verify a raw token and return the service account behind it."""
        with get_db() as db:
            record = db.query(ServiceTokenModel).filter_by(token_hash=hash_secret(secret)).first()
            if not record or record.revoked_at is not None:
                logger.warning("Service token rejected: invalid or revoked")
                raise TokenError("Service token is invalid or revoked")
            if record.expires_at is not None and record.expires_at <= utcnow():
                logger.warning("Service token rejected: expired", token=record.name)
                raise TokenError("Service token expired")

            record.last_used_at = utcnow()
            user_id = record.user_id
            db.commit()

        user = User.get_by_id(user_id)
        if user is None:
            raise TokenError("Service token refers to a user that no longer exists")
        if not user.is_active:
            logger.warning("Service token rejected: inactive account", username=user.username)
            raise TokenError(f"User '{user.username}' is inactive")

        return user

    @classmethod
    def get(cls, user: User, name: str) -> Union["ServiceToken", None]:
        with get_db() as db:
            record = db.query(ServiceTokenModel).filter_by(user_id=user.id, name=name).first()
            if not record:
                logger.debug("Service token not found", username=user.username, token=name)
                return None
            return cls.__from_record(record)

    @classmethod
    def all_for(cls, user: User) -> list["ServiceToken"]:
        """Every token issued to `user`, including revoked and expired ones."""
        with get_db() as db:
            records = db.query(ServiceTokenModel).filter_by(user_id=user.id).all()
            return [cls.__from_record(record) for record in records]

    def revoke(self) -> None:
        """Invalidate this token (no-op if already revoked)."""
        if self.__revoked_at is not None:
            return

        with get_db() as db:
            record = db.query(ServiceTokenModel).filter_by(id=self.__id).first()
            if not record:
                logger.warning("Revoke service token failed: not found", token=self.__name)
                return
            record.revoked_at = utcnow()
            self.__revoked_at = record.revoked_at
            db.commit()

        logger.info("Service token revoked", token=self.__name)

    def delete(self) -> bool:
        with get_db() as db:
            record = db.query(ServiceTokenModel).filter_by(id=self.__id).first()
            if not record:
                return False
            db.delete(record)
            db.commit()

        logger.info("Service token deleted", token=self.__name)
        return True

    @property
    def id(self) -> str:
        return self.__id

    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def secret(self) -> Union[str, None]:
        """The raw token — only available on the object returned by `issue()`."""
        return self.__secret

    @property
    def expires_at(self) -> Union[datetime, None]:
        return self.__expires_at

    @property
    def revoked_at(self) -> Union[datetime, None]:
        return self.__revoked_at

    @property
    def last_used_at(self) -> Union[datetime, None]:
        return self.__last_used_at

    @property
    def is_expired(self) -> bool:
        return self.__expires_at is not None and self.__expires_at <= utcnow()

    @property
    def is_active(self) -> bool:
        return self.__revoked_at is None and not self.is_expired

    @property
    def info(self):
        """Token description. Deliberately omits the secret itself."""
        return asjson({
            "id": self.__id,
            "name": self.__name,
            "user_id": self.__user_id,
            "expires_at": self.__expires_at,
            "revoked_at": self.__revoked_at,
            "last_used_at": self.__last_used_at,
            "is_active": self.is_active,
        })

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.__name
