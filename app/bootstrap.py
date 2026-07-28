"""Startup setup: load config, bring up server state, prepare auth defaults.

A library of small operations that `server.start()` calls in sequence —
nothing here runs on import. Anything that touches existing data
(`create_admin`) is safe to repeat: it fills in what is missing and leaves
the rest alone, so restarting the server never undoes an admin's later
changes (a rotated password, an edited role).
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from app import controller
from core.auth.Group import Group
from core.auth.Role import Role
from core.auth.Session import Session
from core.auth.User import User
from data import database
from utils import logger
from utils.security import generate_password, generate_secret


class BootstrapError(Exception):
    """Raised when startup configuration is missing something required."""


config: dict = None


def load() -> None:
    global config

    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)


def init(token_secret: str) -> None:
    global config

    logger.init(config["logger"])
    logger.info("Logger initialized")

    database.init_db(config["database"])
    logger.info("Database initialized", url=config["database"].get("url"))

    controller.init(config["catalog"], config["workspace"])
    logger.info(
        "Controller ready",
        catalog=config["catalog"].get("path"),
        workspace=config["workspace"].get("path"),
    )


    token_config = (config.get("auth") or {}).get("token") or {}

    algorithm = token_config.get("algorithm", "HS256")
    access_ttl_minutes = token_config.get("access_ttl_minutes", 15)
    refresh_ttl_days = token_config.get("refresh_ttl_days", 30)

    Session.init(token_secret, algorithm, access_ttl_minutes, refresh_ttl_days)
    logger.info("Auth token signing initialized")


def create_admin() -> User:
    global config

    role = Role.get_or_create(
        "admin",
        permissions=[Role.WILDCARD],
        description="Full access to everything.",
    )
    group = Group.get_or_create(
        "Admins",
        role=role,
        description="Default administrators group.",
    )

    admin_config = (config.get("auth") or {}).get("admin") or {}
    users: list[User] = []
    for username, user_config in admin_config.items():
        if User.get(username) is not None:
            logger.debug("Admin user already exists; skipping", username=username)
            continue

        password = generate_password()
        user = User.create(username, password, groups=[group])

        pass_path = user_config.get("pass-path")
        if pass_path:
            pass_path: Path = Path(pass_path)
            pass_path.parent.mkdir(parents=True, exist_ok=True)
            pass_path.write_text(password, encoding="utf-8")

            try:
                pass_path.chmod(0o600)
            except OSError:
                logger.warning("Could not restrict file permissions", path=str(pass_path))

        logger.info("Admin user created", username=username, credentials_path=pass_path)
        users.append(user)

    return users[0] if len(users) > 0 else None


def create_token_secret() -> str:
    global config
    token_config = (config.get("auth") or {}).get("token") or {}

    secret_path = token_config.get("secret-path")
    if not secret_path:
        raise BootstrapError("auth.token.secret-path is not configured")

    secret_path: Path = Path(secret_path)
    secret_path.parent.mkdir(parents=True, exist_ok=True)

    secret = secret_path.read_text(encoding="utf-8").strip() if secret_path.exists() else None
    if secret:
        return secret

    secret = generate_secret()
    secret_path.write_text(secret, encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except OSError:
        logger.warning("Could not restrict file permissions", path=str(secret_path))

    logger.info("Token signing secret generated", path=str(secret_path))
    return secret

