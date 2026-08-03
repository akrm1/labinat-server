"""Permission enforcement: reads allowed for a reader, writes require permission."""

from tests.interface.api.conftest import auth_header


def test_reader_can_read_the_catalog(client, reader_token):
    response = client.get("/catalog/factories", headers=auth_header(reader_token))
    assert response.status_code == 200
    assert response.json() == []


def test_reader_cannot_create_a_factory(client, reader_token):
    response = client.post(
        "/catalog/factories",
        headers=auth_header(reader_token),
        json={"name": "demo", "version": "v1", "data": {}, "frames": []},
    )
    assert response.status_code == 403


def test_reader_can_list_projects(client, reader_token):
    response = client.get("/projects", headers=auth_header(reader_token))
    assert response.status_code == 200
    assert response.json() == []


def test_reader_cannot_create_a_project(client, reader_token):
    response = client.post(
        "/projects",
        headers=auth_header(reader_token),
        json={"name": "p1", "description": ""},
    )
    assert response.status_code == 403


def test_reader_cannot_touch_admin_endpoints(client, reader_token):
    assert client.get("/admin/users", headers=auth_header(reader_token)).status_code == 403


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/catalog/factories").status_code == 403


def test_admin_can_reach_admin_endpoints(client, admin_token):
    response = client.get("/admin/users", headers=auth_header(admin_token))
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert {"admin", "reader"} <= usernames
