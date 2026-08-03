"""Fixtures for API tests.

Each test gets an isolated SQLite DB, temp catalog/workspace, and a seeded
admin plus a limited reader. The FastAPI app is used without its lifespan
(TestClient is not entered as a context manager), so state comes from here
rather than from `config.yaml`.
"""

import pytest
from fastapi.testclient import TestClient

from app import controller
from app.interface.api.app import create_app
from app.core.auth.Group import Group
from app.core.auth.Role import Role
from app.core.auth.User import User
from app.core.auth.Session import Session
from data import database
from utils import logger


@pytest.fixture
def env(tmp_path):
    logger.init({"name": "test-api", "level": "debug", "handlers": {"console": {}}})

    db_path = tmp_path / "api.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    Session.init("test-secret", "HS256", 15, 30)

    catalog_dir = tmp_path / "catalog"
    workspace_dir = tmp_path / "workspace"
    (catalog_dir / "factories").mkdir(parents=True)
    (catalog_dir / "schemas").mkdir(parents=True)
    workspace_dir.mkdir(parents=True)
    controller.init({"path": str(catalog_dir)}, {"path": str(workspace_dir)})

    admin_role = Role.get_or_create("admin", permissions=[Role.WILDCARD])
    admin_group = Group.get_or_create("Admins", role=admin_role)
    User.create("admin", "admin-pw", groups=[admin_group])

    reader_role = Role.get_or_create("reader", permissions=["catalog:read", "project:read"])
    reader_group = Group.get_or_create("Readers", role=reader_role)
    User.create("reader", "reader-pw", groups=[reader_group])

    yield {"tmp_path": tmp_path, "catalog_dir": catalog_dir, "workspace_dir": workspace_dir}

    database.engine.dispose()
    logger.reset()


@pytest.fixture
def client(env):
    return TestClient(create_app())


def login(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token(client):
    return login(client, "admin", "admin-pw")["access_token"]


@pytest.fixture
def reader_token(client):
    return login(client, "reader", "reader-pw")["access_token"]
