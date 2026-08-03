"""FastAPI application factory.

Pure assembly of the REST surface: routers, error handlers, and docs. It knows
nothing about process lifecycle or the MCP surface — `app.server` owns
startup/shutdown, passes in a `lifespan`, and mounts MCP alongside it. This keeps
the dependency pointing one way (server → surfaces).
"""

from typing import Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.base.Schema import FailureError
from app.base.types.DataType import DecodingError
from app.base.Packager import PackagerError
from app.base.PipelineExecuter import PipelineError
from app.base.ImageBuilder import ImageBuildError
from app.base.Tokenizer import TokenError
from app.core.auth.User import UserError, InvalidCredentialsError, PermissionDeniedError
from app.core.auth.Role import RoleError
from app.core.auth.Group import GroupError

from app.interface.api.routers import auth, catalog, projects, operations, admin


DESCRIPTION = (
    "REST API for labinat: manage the catalog (factories & frames), workspace "
    "projects and blocks, run build/package operations with live log streaming, "
    "and administer users, roles, and groups."
)


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(_: Request, exc: InvalidCredentialsError):
        return _error(401, str(exc))

    @app.exception_handler(TokenError)
    async def _token_error(_: Request, exc: TokenError):
        return _error(401, str(exc))

    @app.exception_handler(PermissionDeniedError)
    async def _permission_denied(_: Request, exc: PermissionDeniedError):
        return _error(403, str(exc))

    @app.exception_handler(FailureError)
    async def _validation(_: Request, exc: FailureError):
        return _error(400, str(exc))

    @app.exception_handler(DecodingError)
    async def _decoding(_: Request, exc: DecodingError):
        return _error(400, str(exc))

    @app.exception_handler(PackagerError)
    async def _packager(_: Request, exc: PackagerError):
        return _error(409, str(exc))

    @app.exception_handler(UserError)
    async def _user(_: Request, exc: UserError):
        return _error(409, str(exc))

    @app.exception_handler(RoleError)
    async def _role(_: Request, exc: RoleError):
        return _error(409, str(exc))

    @app.exception_handler(GroupError)
    async def _group(_: Request, exc: GroupError):
        return _error(409, str(exc))

    @app.exception_handler(PipelineError)
    async def _pipeline(_: Request, exc: PipelineError):
        return _error(500, str(exc))

    @app.exception_handler(ImageBuildError)
    async def _image_build(_: Request, exc: ImageBuildError):
        return _error(500, str(exc))


def create_app(lifespan: Optional[Callable] = None) -> FastAPI:
    app = FastAPI(
        title="labinat",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(projects.router)
    app.include_router(operations.router)
    app.include_router(admin.router)

    _register_error_handlers(app)

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok"}

    return app
