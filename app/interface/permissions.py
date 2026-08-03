"""Permission strings enforced across every interface surface.

Defined once here so the REST routers and the MCP tools gate on the exact same
identifiers — change a permission name in one place and both surfaces follow.
Roles grant these (or the wildcard `*`); see `app.core.auth`.
"""

CATALOG_READ = "catalog:read"
CATALOG_WRITE = "catalog:write"

PROJECT_READ = "project:read"
PROJECT_WRITE = "project:write"
PROJECT_EXECUTE = "project:execute"

ADMIN_READ = "admin:read"
ADMIN_WRITE = "admin:write"
