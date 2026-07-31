from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from data.models.BaseModel import BaseModel

engine = None
SessionLocal = None


def __configure_sqlite(dbapi_connection, connection_record):
    """Apply the per-connection pragmas SQLite does not enable by default.

    `foreign_keys` is off unless asked for, which leaves every
    `ForeignKeyConstraint` in `data.models` decorative and lets orphaned rows
    (blocks, memberships, tokens) accumulate unnoticed. WAL is set alongside
    it so readers are not blocked by a writer.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def init_db(database_config: dict):
    global engine, SessionLocal

    url = database_config["url"]
    logging = database_config["logging"]
    is_sqlite = url.startswith("sqlite")

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        echo=logging,
    )
    if is_sqlite:
        event.listen(engine, "connect", __configure_sqlite)

    SessionLocal = sessionmaker(engine, expire_on_commit=False)
    BaseModel.metadata.create_all(engine)


@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
