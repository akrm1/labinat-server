import pytest

from app import bootstrap
from core.auth.Group import Group
from core.auth.Role import Role
from core.auth.Session import Session
from core.auth.User import User
from data import database


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    yield
    database.engine.dispose()


@pytest.fixture(autouse=True)
def _reset_bootstrap_config():
    yield
    bootstrap.config = None


def set_auth_config(tmp_path, admin=None):
    bootstrap.config = {
        "auth": {
            "token": {"secret-path": str(tmp_path / "jwt-secret")},
            "admin": admin or {},
        }
    }


# --- load ----------------------------------------------------------------

def test_load_reads_config_yaml_from_the_cwd(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("workspace:\n  path: workspace\n")
    monkeypatch.chdir(tmp_path)

    bootstrap.load()
    assert bootstrap.config == {"workspace": {"path": "workspace"}}


# --- create_admin: role and group ----------------------------------

def test_create_admin_creates_the_role_and_group(db, tmp_path):
    set_auth_config(tmp_path)
    bootstrap.create_admin()

    role = Role.get("admin")
    group = Group.get("Admins")
    assert role.permissions == [Role.WILDCARD]
    assert group.role.id == role.id


def test_create_admin_role_and_group_are_idempotent(db, tmp_path):
    set_auth_config(tmp_path)
    bootstrap.create_admin()
    bootstrap.create_admin()  # should not raise

    assert Role.get("admin").permissions == [Role.WILDCARD]
    assert list(Group.all().keys()) == ["Admins"]


# --- create_admin: users ------------------------------------------------

def test_create_admin_creates_every_configured_user(db, tmp_path):
    pass_path = tmp_path / "lab_admin-password"
    set_auth_config(tmp_path, {"lab_admin": {"pass-path": str(pass_path)}})

    admin = bootstrap.create_admin()

    user = User.get("lab_admin")
    assert admin.username == "lab_admin"
    assert list(user.groups.keys()) == ["Admins"]
    assert user.has_permission("anything:at-all") is True
    assert user.verify_password(pass_path.read_text().strip()) is True


def test_create_admin_writes_an_owner_only_password_file(db, tmp_path):
    pass_path = tmp_path / "lab_admin-password"
    set_auth_config(tmp_path, {"lab_admin": {"pass-path": str(pass_path)}})
    bootstrap.create_admin()

    assert pass_path.stat().st_mode & 0o777 == 0o600


def test_create_admin_without_pass_path_refuses_to_create_the_user(db, tmp_path):
    """The password is generated during bootstrap and never asked for again,
    so with nowhere to write it the account would be unreachable forever."""
    set_auth_config(tmp_path, {"lab_admin": {}})

    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.create_admin()

    assert User.get("lab_admin") is None


def test_create_admin_leaves_existing_users_untouched(db, tmp_path):
    pass_path = tmp_path / "lab_admin-password"
    set_auth_config(tmp_path, {"lab_admin": {"pass-path": str(pass_path)}})

    bootstrap.create_admin()
    User.get("lab_admin").set_password("changed-by-the-admin")
    pass_path.unlink()

    set_auth_config(tmp_path, {"lab_admin": {"pass-path": str(pass_path)}})
    bootstrap.create_admin()  # second boot

    assert User.get("lab_admin").verify_password("changed-by-the-admin") is True
    assert not pass_path.exists()


def test_create_admin_supports_multiple_admins(db, tmp_path):
    set_auth_config(tmp_path, {
        "lab_admin": {"pass-path": str(tmp_path / "lab_admin-password")},
        "ops_admin": {"pass-path": str(tmp_path / "ops_admin-password")},
    })
    bootstrap.create_admin()
    assert sorted(User.all().keys()) == ["lab_admin", "ops_admin"]


def test_create_admin_with_no_admins_configured_still_seeds_role(db, tmp_path):
    set_auth_config(tmp_path)
    result = bootstrap.create_admin()

    assert result is None
    assert User.all() == {}
    assert Role.get("admin") is not None  # role/group still seeded


# --- create_token_secret -------------------------------------------

def test_create_token_secret_generates_on_first_run(tmp_path):
    secret_path = tmp_path / "jwt-secret"
    set_auth_config(tmp_path)

    secret = bootstrap.create_token_secret()

    assert secret_path.read_text().strip() == secret
    assert secret_path.stat().st_mode & 0o777 == 0o600


def test_create_token_secret_reuses_the_existing_file(tmp_path):
    set_auth_config(tmp_path)

    first = bootstrap.create_token_secret()
    second = bootstrap.create_token_secret()

    assert first == second


def test_create_token_secret_does_not_rewrite_an_unchanged_secret(tmp_path):
    secret_path = tmp_path / "jwt-secret"
    set_auth_config(tmp_path)

    bootstrap.create_token_secret()
    written_at = secret_path.stat().st_mtime_ns

    bootstrap.create_token_secret()
    assert secret_path.stat().st_mtime_ns == written_at


def test_create_token_secret_regenerates_an_empty_file(tmp_path):
    secret_path = tmp_path / "jwt-secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_path.write_text("   \n")
    set_auth_config(tmp_path)

    secret = bootstrap.create_token_secret()
    assert secret_path.read_text().strip() == secret


def test_create_token_secret_without_secret_path_raises(tmp_path):
    bootstrap.config = {"auth": {"token": {}}}
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.create_token_secret()


def test_create_token_secret_without_auth_config_raises():
    bootstrap.config = {}
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.create_token_secret()


# --- init: token signing wiring -------------------------------------

def test_init_wires_up_session_signing(db, tmp_path):
    set_auth_config(tmp_path)
    bootstrap.config["database"] = {"url": f"sqlite:///{tmp_path / 'init.db'}", "logging": False}
    bootstrap.config["catalog"] = {"path": str(tmp_path / "catalog")}
    bootstrap.config["workspace"] = {"path": str(tmp_path / "workspace")}
    bootstrap.config["logger"] = {"name": "test-app", "handlers": {"console": {}}}

    secret = bootstrap.create_token_secret()
    bootstrap.init(secret)

    user = User.create("alice", "pass")
    session = user.login("pass")
    assert Session.authenticate(session.access_token).username == "alice"
