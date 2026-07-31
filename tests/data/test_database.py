import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from data import database
# Both parents must be registered on the metadata for create_all to resolve
# the composite foreign keys `project_factories` declares against them.
from data.models.FactoryModel import FactoryModel  # noqa: F401
from data.models.ProjectModel import ProjectModel  # noqa: F401
from data.models.ProjectFactoryModel import ProjectFactoryModel


@pytest.fixture
def db(tmp_path):
    database.init_db({"url": f"sqlite:///{tmp_path / 'test.db'}", "logging": False})
    yield
    database.engine.dispose()


def test_sqlite_connections_enforce_foreign_keys(db):
    """SQLite disables foreign keys per connection unless asked, which would
    make every ForeignKeyConstraint in data.models decorative."""
    with database.get_db() as session:
        assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_sqlite_connections_use_write_ahead_logging(db):
    with database.get_db() as session:
        assert session.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_a_row_referencing_a_missing_parent_is_rejected(db):
    """The pragma is only worth setting if it actually bites: a join row whose
    project and factory do not exist must not be insertable."""
    with pytest.raises(IntegrityError):
        with database.get_db() as session:
            session.add(ProjectFactoryModel(
                project_id="no-such-project",
                factory="no-such-factory",
                factory_version="v1",
            ))
            session.commit()
