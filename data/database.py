from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from data.models.BaseModel import BaseModel

engine = None
SessionLocal = None


def init_db(database_config: dict):
    global engine, SessionLocal

    url = database_config["url"]
    logging = database_config["logging"]

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
        echo=logging,
    )
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
