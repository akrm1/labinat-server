"""Server entry point: wires up `bootstrap`'s setup steps in sequence."""

from app import bootstrap


def start() -> dict:
    """Bring the whole server up: config → logger/db/controller → auth."""

    bootstrap.load()

    token_secret = bootstrap.create_token_secret()
    bootstrap.init(token_secret)
    bootstrap.create_admin()

    return bootstrap.config
