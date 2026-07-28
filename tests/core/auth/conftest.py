import pytest

from data import database


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    yield
    database.engine.dispose()
