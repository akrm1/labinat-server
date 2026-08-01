"""Representative project lifecycle over HTTP: create, list, get, delete."""

from tests.api.conftest import auth_header


def test_project_crud_roundtrip(client, admin_token):
    headers = auth_header(admin_token)

    created = client.post(
        "/projects",
        headers=headers,
        json={"name": "my_site", "description": "demo", "config": {"app": {"name": "my_site"}}},
    )
    assert created.status_code == 201, created.text
    project = created.json()
    project_id = project["id"]
    assert project["name"] == "my_site"

    listed = client.get("/projects", headers=headers)
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    fetched = client.get(f"/projects/{project_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "demo"

    deleted = client.delete(f"/projects/{project_id}", headers=headers)
    assert deleted.status_code == 200

    assert client.get(f"/projects/{project_id}", headers=headers).status_code == 404


def test_get_unknown_project_is_404(client, admin_token):
    response = client.get("/projects/does-not-exist", headers=auth_header(admin_token))
    assert response.status_code == 404
