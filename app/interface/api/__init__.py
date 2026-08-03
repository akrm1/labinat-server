"""REST surface for labinat: a FastAPI app exposing the domain over HTTP."""

from app.interface.api.app import create_app

__all__ = ["create_app"]
