"""Server controller: bootstrap, app building, and launching.

Each method is a single, independent step. `main.py` is the orchestrator that
calls them in order and threads the config returned by `start()` into `run()`;
the methods do not call one another.
"""

import uvicorn

from app import bootstrap
from app.api.app import create_app
from utils import logger


def start() -> dict:
    """Bootstrap the server (config → logger/db/controller → auth); returns config."""

    bootstrap.load()

    token_secret = bootstrap.create_token_secret()
    bootstrap.init(token_secret)
    bootstrap.create_admin()

    return bootstrap.config


def run(host: str, port: int, reload: bool = False) -> None:
    """Serve the REST API with uvicorn. Blocks until the server stops."""

    uvicorn.run(create_app(), host=host, port=port, reload=reload)


def shutdown() -> None:
    """Collapse any in-flight operations so no subprocess is left orphaned."""

    from app.api import operations

    collapsed = operations.collapse()
    if collapsed:
        logger.info("Collapsed running operations on shutdown", operations=collapsed)
