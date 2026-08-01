"""HTTP layer for labinat: a FastAPI app exposing the domain over REST."""

from app.api.app import create_app

__all__ = ["create_app"]
