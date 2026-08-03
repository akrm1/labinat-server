"""The interface layer: how the outside world drives labinat's domain.

Two surfaces are served from one app — a REST API (`api/`) and an MCP server
(`mcp/`) — and they share this package's base modules so a change is reflected in
both:

- `serializers`  — domain objects → JSON-serializable dicts
- `permissions`  — the permission strings both surfaces enforce
- `identity`     — resolve a bearer token to a `User`

Each surface is a thin adapter over this shared base; `app.server` composes them
into a single server.
"""
