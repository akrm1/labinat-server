# Configuration

How Labinat is configured, where it keeps its files, and how to run it in development and production.

---

## Precedence

Configuration is resolved once at startup, in this order (later wins):

1. **Built-in defaults** — baked into [`app/bootstrap.py`](../app/bootstrap.py) as the `config` dict. These use production (FHS) paths so the server can run with **no config file at all**.
2. **A config file** — YAML named by the `LABINAT_CONFIG` environment variable. When set, it is **deep-merged** over the defaults (see [`utils.helpers.override_dict`](../utils/helpers.py)).
3. **Environment variables** — a few `LABINAT_*` variables read by [`main.py`](../main.py) for the bind address and reload flag.

If `LABINAT_CONFIG` is unset (or the file can't be read), Labinat logs a warning and runs on the defaults.

> **One special case — `auth.admins` replaces, it does not merge.** A config file that defines `auth.admins` replaces the default admin map wholesale rather than unioning with it. This keeps the built-in default admin (and its `/var/lib` password path) from tagging along into a deployment that defines its own admins. Every other section is deep-merged normally.

---

## Default configuration

The built-in defaults, expressed as YAML:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  reload: false
  mcp:
    enabled: true
    path: "/mcp"

catalog:
  path: "/var/lib/labinat/catalog"

workspace:
  path: "/srv/labinat/workspace"

database:
  url: "sqlite:////var/lib/labinat/database.db"
  logging: false

auth:
  token:
    secret-path: "/var/lib/labinat/secrets/jwt-secret"
    algorithm: "HS256"
    access_ttl_minutes: 15
    refresh_ttl_days: 30
  admins:
    labadmin:
      pass-path: "/var/lib/labinat/secrets/lab_admin-password"

logger:
  name: "app"
  level: "info"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  datefmt: "%Y-%m-%d %H:%M:%S"
  handlers:
    console: {}
    file:
      path: "/var/log/labinat.log"
```

A config file only needs to specify the keys it wants to override; everything else falls back to these defaults.

---

## Settings reference

### `server`

| Key | Default | Meaning |
|-----|---------|---------|
| `host` | `0.0.0.0` | Bind address. Overridable with `LABINAT_HOST`. |
| `port` | `8000` | Bind port. Overridable with `LABINAT_PORT`. |
| `reload` | `false` | uvicorn auto-reload (development). Overridable with `LABINAT_RELOAD`. |
| `mcp.enabled` | `true` | Mount the MCP surface. When `false`, only the REST API is served. |
| `mcp.path` | `/mcp` | Path the MCP server is mounted under, on the same app/port. |

The MCP endpoint's advertised URL (used in its OAuth resource metadata) is derived from `host`/`port`; `0.0.0.0`/`::` are advertised as `localhost`.

### `catalog` / `workspace`

| Key | Default | Meaning |
|-----|---------|---------|
| `catalog.path` | `/var/lib/labinat/catalog` | On-disk factory artifacts (frames, concretes, bindings, `base/`). |
| `workspace.path` | `/srv/labinat/workspace` | Projects and their generated `src/`. Kept separate because it grows over time. |

### `database`

| Key | Default | Meaning |
|-----|---------|---------|
| `database.url` | `sqlite:////var/lib/labinat/database.db` | SQLAlchemy URL. SQLite parent directory is created automatically. |
| `database.logging` | `false` | Echo SQL statements. |

Other SQLAlchemy backends (e.g. PostgreSQL) work by setting a different URL.

### `auth`

| Key | Default | Meaning |
|-----|---------|---------|
| `auth.token.secret-path` | `/var/lib/labinat/secrets/jwt-secret` | HMAC key that signs access tokens. Generated on first run (mode `600`), then left untouched. Delete to rotate (logs everyone out). |
| `auth.token.algorithm` | `HS256` | JWT signing algorithm. |
| `auth.token.access_ttl_minutes` | `15` | Access-token lifetime. |
| `auth.token.refresh_ttl_days` | `30` | Refresh-token lifetime. |
| `auth.admins` | one `labadmin` | Map of admin accounts to seed. **The key is the username.** Each gets a random password written to its `pass-path`. |

Admins are seeded once and then left alone — a restart never overwrites a rotated password or an edited role. See [Concepts → Bootstrap](Concepts.md#bootstrap).

### `logger`

Standard Python logging config consumed by [`utils/logger.py`](../utils/logger.py): `name`, `level`, `format`, `datefmt`, and `handlers` (`console` and/or `file`). Set `level: debug` to see domain construct/validate traces. Omit the `file` handler (or point it at `stdout`) to log to the console only.

---

## Environment variables

| Variable | Applies to | Notes |
|----------|-----------|-------|
| `LABINAT_CONFIG` | config file path | When set, deep-merged over the defaults. When it points at a missing/unreadable file, Labinat warns and uses the defaults. |
| `LABINAT_HOST` | `server.host` | Bind address override. |
| `LABINAT_PORT` | `server.port` | Bind port override. |
| `LABINAT_RELOAD` | `server.reload` | `1`/`true`/`yes` enable uvicorn reload. |

---

## Filesystem layout

Labinat creates the directories it needs on every start, **idempotently** — existing directories and their contents are left untouched, so it is safe to run over live data (a restart or reinstall never wipes anything). Creation is split across the modules that own each path:

| Created by | Directories |
|-----------|-------------|
| [`bootstrap.init`](../app/bootstrap.py) | log-file dir, token-secret dir, each admin `pass-path` dir |
| [`bootstrap.create_token_secret`](../app/bootstrap.py) | token-secret dir (before writing the key) |
| [`controller.init`](../app/controller.py) | `catalog/` (+ `factories`, `schemas`, `templates`), `workspace/` (+ `projects`) |
| [`database.init_db`](../data/database.py) | SQLite database parent dir |

Recommended production locations (the defaults) follow the Filesystem Hierarchy Standard:

| Data | Default path | FHS rationale |
|------|--------------|---------------|
| Catalog artifacts | `/var/lib/labinat/catalog` | Application state |
| Database | `/var/lib/labinat/database.db` | Application state |
| Secrets | `/var/lib/labinat/secrets/` | Application state (mode `600`) |
| Workspace | `/srv/labinat/workspace` | Served/site data; grows over time, easy to mount on its own disk |
| Logs | `/var/log/labinat.log` | Logs |

### Secrets

Generated secrets are written with mode `600` and are gitignored:

- `auth/*-secret` — the JWT signing key.
- `auth/*-password` — seeded admin passwords.

Both are read-once conveniences: the JWT key persists across restarts; admin passwords are generated once and should be rotated by the operator afterward.

---

## Running in development

The defaults target `/var/lib`, `/srv`, and `/var/log`, which are not writable on a typical dev machine. Point `LABINAT_CONFIG` at a file with project-relative paths (see the example in the [README quickstart](../README.md#quickstart)):

```bash
LABINAT_CONFIG=labinat.dev.yaml python main.py
```

To serve REST only (no MCP) while iterating, set `server.mcp.enabled: false`.

---

## Running in production

1. Create the state directories and grant ownership to the service user, e.g.:
   ```bash
   sudo mkdir -p /var/lib/labinat/secrets /srv/labinat/workspace
   sudo chown -R labinat:labinat /var/lib/labinat /srv/labinat
   ```
   (Labinat will also create missing directories on start, provided it has permission.)
2. Run behind a reverse proxy that terminates TLS. If the public URL differs from the bind address, set `server.mcp.public_url` so MCP advertises a reachable URL.
3. Start `python main.py` under a process manager (systemd, container runtime, …).

### Containers

Mount the two state roots as volumes and point config at them (or just rely on the defaults, which already live under `/var/lib` and `/srv`):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
VOLUME ["/var/lib/labinat", "/srv/labinat"]
EXPOSE 8000
CMD ["python", "main.py"]
```

Because directory creation is idempotent, the same image works for a first install and for restarts over an existing volume. Keep the workspace volume separate from the catalog/database volume so it can grow (and be backed up) independently.
