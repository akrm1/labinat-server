"""RBAC admin over HTTP: roles, groups, users, and service tokens."""

from tests.api.conftest import auth_header


def test_create_role_group_and_user(client, admin_token):
    headers = auth_header(admin_token)

    role = client.post(
        "/admin/roles",
        headers=headers,
        json={"name": "editors", "permissions": ["catalog:read", "catalog:write"]},
    )
    assert role.status_code == 201, role.text

    group = client.post(
        "/admin/groups",
        headers=headers,
        json={"name": "Editors", "role": "editors"},
    )
    assert group.status_code == 201, group.text

    user = client.post(
        "/admin/users",
        headers=headers,
        json={"username": "erin", "password": "erin-pw", "groups": ["Editors"]},
    )
    assert user.status_code == 201, user.text
    assert set(user.json()["permissions"]) >= {"catalog:read", "catalog:write"}

    # The new user can log in and use their write permission.
    login = client.post("/auth/login", json={"username": "erin", "password": "erin-pw"})
    assert login.status_code == 200
    erin_headers = auth_header(login.json()["access_token"])
    assert client.get("/catalog/factories", headers=erin_headers).status_code == 200


def test_service_account_token_authenticates(client, admin_token):
    headers = auth_header(admin_token)

    account = client.post(
        "/admin/service-accounts",
        headers=headers,
        json={"username": "ci-bot", "groups": []},
    )
    assert account.status_code == 201, account.text
    assert account.json()["is_service"] is True

    token = client.post(
        "/admin/users/ci-bot/tokens",
        headers=headers,
        json={"name": "pipeline"},
    )
    assert token.status_code == 201, token.text
    secret = token.json()["secret"]
    assert secret

    # The raw secret works as a bearer token for the service account.
    me = client.get("/auth/me", headers=auth_header(secret))
    assert me.status_code == 200
    assert me.json()["username"] == "ci-bot"
    assert me.json()["is_service"] is True


def test_revoked_service_token_stops_working(client, admin_token):
    headers = auth_header(admin_token)
    client.post("/admin/service-accounts", headers=headers, json={"username": "bot2", "groups": []})
    secret = client.post(
        "/admin/users/bot2/tokens", headers=headers, json={"name": "t"}
    ).json()["secret"]

    assert client.get("/auth/me", headers=auth_header(secret)).status_code == 200

    revoked = client.delete("/admin/users/bot2/tokens/t", headers=headers)
    assert revoked.status_code == 200

    assert client.get("/auth/me", headers=auth_header(secret)).status_code == 401
