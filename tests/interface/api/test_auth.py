"""Auth flow: login, current user, refresh rotation, logout, and token errors."""

from tests.interface.api.conftest import auth_header, login


def test_login_returns_a_token_pair(client):
    body = login(client, "admin", "admin-pw")
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] > 0


def test_login_with_a_wrong_password_is_401(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client, admin_token):
    response = client.get("/auth/me", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_a_missing_bearer_is_rejected(client):
    assert client.get("/auth/me").status_code == 403


def test_an_invalid_bearer_is_401(client):
    response = client.get("/auth/me", headers=auth_header("not-a-real-token"))
    assert response.status_code == 401


def test_refresh_rotates_the_refresh_token(client):
    tokens = login(client, "admin", "admin-pw")
    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200

    rotated = response.json()
    # The refresh token is a fresh random secret; the old one is now revoked.
    assert rotated["refresh_token"] != tokens["refresh_token"]
    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    tokens = login(client, "admin", "admin-pw")
    assert client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 200

    replay = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
