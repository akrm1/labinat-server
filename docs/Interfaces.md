# Interfaces

Labinat exposes its domain through two surfaces served from **one process on one port**: a **REST API** and an **MCP** server. Both are thin adapters over the same domain layer and share serializers, permission strings, and identity resolution, so a change is reflected in both.

- **REST API** — mounted at the root. Interactive docs (Swagger UI) at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`, health at `/health`.
- **MCP** — mounted at `/mcp` (configurable via `server.mcp.path`), served over Streamable HTTP.

Both are composed and served by [`app/server.py`](../app/server.py). Set `server.mcp.enabled: false` to serve REST only.

---

## Authentication

Every request (except the public endpoints below) must carry a **bearer token** in the `Authorization` header. A token is one of:

- a **session access token** — obtained by a human logging in with a username and password; short-lived and paired with a rotatable refresh token;
- a **service-account token** — a long-lived API secret minted for non-human callers.

Both surfaces resolve tokens through the same code ([`app/interface/identity.py`](../app/interface/identity.py)), so they accept identical credentials.

### Login flow (REST)

```bash
# 1. Log in → access + refresh tokens
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "lab_admin", "password": "<password>"}'
# → { "access_token": "...", "refresh_token": "...", "token_type": "bearer", ... }

# 2. Call an authenticated endpoint
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"

# 3. Rotate when the access token expires (the refresh token is single-use)
curl -s -X POST http://localhost:8000/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "<refresh_token>"}'
```

`refresh` rotates the pair: the old refresh token is revoked and a new pair issued, so a captured token is single-use. `logout` revokes a refresh token.

**Public endpoints** (no token): `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /health`, and the docs routes.

---

## Authorization (RBAC)

A user's effective permissions are the **union** of the roles reachable through their groups (`User → Group → Role → permissions[]`). More group membership only ever adds rights; there is no deny list. The wildcard `*` grants everything (the seeded `admin` role holds it).

The same permission strings gate both surfaces:

| Permission | Grants |
|-----------|--------|
| `catalog:read` | Read factories and frames |
| `catalog:write` | Create/update/delete factories and frames; import/export |
| `project:read` | Read projects and blocks |
| `project:write` | Create/update/delete projects and blocks; attach factories |
| `project:execute` | Run build/emit/run/debug/package operations |
| `admin:read` | Read users, roles, groups, tokens |
| `admin:write` | Manage users, service accounts, roles, groups, tokens |
| `*` | Everything |

A REST call lacking the required permission returns `403`; an MCP tool raises an authorization error.

---

## REST endpoints

All non-auth endpoints require a bearer token **and** the listed permission.

### Auth — `/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | public | Exchange username/password for tokens |
| POST | `/auth/refresh` | public | Rotate the refresh token for a new pair |
| POST | `/auth/logout` | public | Revoke a refresh token |
| GET | `/auth/me` | any user | The current user |

### Catalog — `/catalog`

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/catalog/factories` | `catalog:read` | List factories |
| POST | `/catalog/factories` | `catalog:write` | Create a factory version |
| GET | `/catalog/factories/{name}/{version}` | `catalog:read` | Get a factory |
| PUT | `/catalog/factories/{name}/{version}` | `catalog:write` | Update a factory's data |
| DELETE | `/catalog/factories/{name}/{version}` | `catalog:write` | Delete a factory version |
| POST | `/catalog/factories/{name}/{version}/frames` | `catalog:write` | Add a frame |
| GET | `/catalog/factories/{name}/{version}/frames/{frame}` | `catalog:read` | Get a frame |
| PUT | `/catalog/factories/{name}/{version}/frames/{frame}` | `catalog:write` | Update a frame |
| DELETE | `/catalog/factories/{name}/{version}/frames/{frame}` | `catalog:write` | Delete a frame |
| POST | `/catalog/factories/{name}/{version}/export?dest_path=…` | `catalog:read` | Export a factory to a `.tar.gz` |
| POST | `/catalog/import?archive_path=…&overwrite=…` | `catalog:write` | Import a factory package |

### Projects — `/projects`

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/projects` | `project:read` | List projects |
| POST | `/projects` | `project:write` | Create a project (optionally attach factories) |
| GET | `/projects/{project_id}` | `project:read` | Get a project |
| DELETE | `/projects/{project_id}` | `project:write` | Delete a project (and its on-disk tree) |
| POST | `/projects/{project_id}/factories` | `project:write` | Attach a factory to a project |
| GET | `/projects/{project_id}/blocks` | `project:read` | List blocks |
| POST | `/projects/{project_id}/blocks` | `project:write` | Create a block |
| GET | `/projects/{project_id}/blocks/{block_name}` | `project:read` | Get a block |
| DELETE | `/projects/{project_id}/blocks` | `project:write` | Delete named blocks (body: `{ "names": [...] }`) |

### Operations — `/projects/{project_id}` (streamed)

Long-running operations are streamed as **Server-Sent Events** (`text/event-stream`). All require `project:execute`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{project_id}/build` | Scaffold → init → emit → build pipeline |
| POST | `/projects/{project_id}/emit` | Render blocks to source files (returns paths) |
| POST | `/projects/{project_id}/run` | Run pipeline (may be long-running) |
| POST | `/projects/{project_id}/debug` | Debug pipeline (may be long-running) |
| POST | `/projects/{project_id}/package?tool=docker` | Build one container image per factory (returns tags) |

**Event sequence:** a `start` event, a `log` event per output line as the operation runs, then a terminal `completed` (with the result), `error`, or `cancelled` event. **Disconnecting the request cancels the operation** and stops any subprocess it spawned.

### Admin — `/admin`

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/admin/users` | `admin:read` | List users |
| POST | `/admin/users` | `admin:write` | Create a human user |
| POST | `/admin/service-accounts` | `admin:write` | Create a service account |
| GET | `/admin/users/{username}` | `admin:read` | Get a user |
| DELETE | `/admin/users/{username}` | `admin:write` | Delete a user |
| POST | `/admin/users/{username}/activate` | `admin:write` | Activate a user |
| POST | `/admin/users/{username}/deactivate` | `admin:write` | Deactivate (kills sessions & tokens) |
| POST | `/admin/users/{username}/groups` | `admin:write` | Add a user to a group |
| DELETE | `/admin/users/{username}/groups/{group}` | `admin:write` | Remove a user from a group |
| GET | `/admin/users/{username}/tokens` | `admin:read` | List a user's service tokens |
| POST | `/admin/users/{username}/tokens` | `admin:write` | Issue a service token (secret shown once) |
| DELETE | `/admin/users/{username}/tokens/{name}` | `admin:write` | Revoke a token |
| GET | `/admin/roles` | `admin:read` | List roles |
| POST | `/admin/roles` | `admin:write` | Create a role |
| GET | `/admin/roles/{name}` | `admin:read` | Get a role |
| DELETE | `/admin/roles/{name}` | `admin:write` | Delete a role |
| PUT | `/admin/roles/{name}/permissions` | `admin:write` | Replace a role's permissions |
| GET | `/admin/groups` | `admin:read` | List groups |
| POST | `/admin/groups` | `admin:write` | Create a group (bound to a role) |
| GET | `/admin/groups/{name}` | `admin:read` | Get a group |
| DELETE | `/admin/groups/{name}` | `admin:write` | Delete a group |
| PUT | `/admin/groups/{name}/role` | `admin:write` | Rebind a group to a role |

### Error responses

Domain errors map to HTTP status codes (see [`app/interface/api/app.py`](../app/interface/api/app.py)):

| Status | Raised by |
|--------|-----------|
| `400` | Schema validation (`FailureError`), decoding (`DecodingError`) |
| `401` | Invalid credentials, invalid/expired token |
| `403` | Permission denied |
| `404` | Resource not found (per-router) |
| `409` | Conflicts: user/role/group errors, packaging errors |
| `500` | Pipeline failure, image build failure |

---

## MCP tools

The MCP server (`labinat`) exposes the same operations as tools over Streamable HTTP, secured with the same bearer tokens and permissions. Because it is network-exposed, **every request must present a valid labinat token**, and each tool enforces its permission just like the REST surface.

Unlike REST (which streams operations over SSE), MCP is request/response: an operation tool runs to completion and returns the captured logs with the result.

### `catalog`

| Tool | Permission | Description |
|------|-----------|-------------|
| `list_factories` | `catalog:read` | List every factory and version |
| `get_factory` | `catalog:read` | Get a factory version (frames, config, pipelines) |
| `create_factory` | `catalog:write` | Create a factory version and scaffold frames |
| `get_frame` | `catalog:read` | Get a frame's spec and concretes |
| `create_frame` | `catalog:write` | Add a frame to a factory version |

### `projects`

| Tool | Permission | Description |
|------|-----------|-------------|
| `list_projects` | `project:read` | List every project |
| `get_project` | `project:read` | Get a project (factories and blocks) |
| `create_project` | `project:write` | Create a project, optionally attaching factories |
| `delete_project` | `project:write` | Delete a project and its on-disk tree |
| `add_factory` | `project:write` | Attach a factory version to a project |
| `list_blocks` | `project:read` | List a project's blocks |
| `get_block` | `project:read` | Get one block |
| `create_block` | `project:write` | Create a block (an instance of a frame) |
| `delete_blocks` | `project:write` | Delete named blocks |

### `operations`

| Tool | Permission | Description |
|------|-----------|-------------|
| `build` | `project:execute` | Run build pipelines; returns logs |
| `emit` | `project:execute` | Render artifacts; returns paths and logs |
| `package` | `project:execute` | Build container image(s); returns tags and logs |
| `run` | `project:execute` | Run pipeline (may be long-running) |
| `debug` | `project:execute` | Debug pipeline (may be long-running) |

> **Naming:** factory, frame, project, and block names must not contain dots (`.`), since dots separate the parts of a [resource identifier](Concepts.md#resource-identifiers).

### Connecting an MCP client

Point your client at the `/mcp` endpoint and pass a labinat token as a bearer header. For a service account, mint a long-lived token via `POST /admin/users/{username}/tokens`. Example (Cursor `mcp.json`):

```json
{
  "mcpServers": {
    "labinat": {
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer <labinat-token>" }
    }
  }
}
```

When Labinat runs behind a reverse proxy on a different public URL, set `server.mcp.public_url` so the advertised OAuth resource metadata is reachable.
