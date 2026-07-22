import logging

import pytest
import yaml

from utils import logger


@pytest.fixture(autouse=True)
def _reset_logger():
    logger.reset()
    yield
    logger.reset()


def test_init_takes_full_config_and_applies_all_fields(tmp_path):
    log_path = tmp_path / "test.log"
    logger.init({
        "name": "test-app",
        "level": "info",
        "format": "%(levelname)s|%(name)s|%(message)s",
        "datefmt": "%Y",
        "handlers": {"file": {"path": str(log_path)}},
    })

    logger.info("hello world")

    content = log_path.read_text()
    assert "INFO|test-app|hello world" in content
    assert logger.get_logger().name == "test-app"
    assert logger.get_logger().level == logging.INFO


def test_init_uses_datefmt_from_config(tmp_path):
    log_path = tmp_path / "date.log"
    logger.init({
        "name": "dated",
        "level": "info",
        "format": "%(asctime)s %(message)s",
        "datefmt": "DATEFMT-OK",
        "handlers": {"file": {"path": str(log_path)}},
    })

    logger.info("ping")
    assert log_path.read_text().startswith("DATEFMT-OK ping")


def test_init_clears_previous_handlers_on_reinit(tmp_path):
    first = tmp_path / "first.log"
    second = tmp_path / "second.log"

    logger.init({"name": "test-app", "handlers": {"file": {"path": str(first)}}})
    logger.init({"name": "test-app", "handlers": {"file": {"path": str(second)}}})
    logger.info("only-second")

    assert "only-second" in second.read_text()
    assert first.exists()
    assert "only-second" not in first.read_text()


def test_severity_helpers_route_to_correct_level(tmp_path):
    log_path = tmp_path / "levels.log"
    logger.init({
        "name": "test-app",
        "level": "debug",
        "format": "%(levelname)s:%(message)s",
        "handlers": {"file": {"path": str(log_path)}},
    })

    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")

    content = log_path.read_text()
    assert "DEBUG:d" in content
    assert "INFO:i" in content
    assert "WARNING:w" in content
    assert "ERROR:e" in content
    assert "CRITICAL:c" in content


def test_extra_kwargs_appended_to_message(tmp_path):
    log_path = tmp_path / "extra.log"
    logger.init({
        "name": "test-app",
        "handlers": {"file": {"path": str(log_path)}},
        "format": "%(message)s",
    })

    logger.info("created", project_id="p1", name="demo")

    line = log_path.read_text().strip()
    assert line.startswith("created |")
    assert "project_id='p1'" in line
    assert "name='demo'" in line


def test_log_works_before_init_via_fallback():
    logger.reset()
    # Must not raise even when init() was never called.
    logger.info("pre-init message")
    assert logger.is_initialized() is False


def test_is_initialized_and_reset():
    assert logger.is_initialized() is False
    logger.init({"name": "test-app", "handlers": {"console": {}}})
    assert logger.is_initialized() is True
    logger.reset()
    assert logger.is_initialized() is False


def test_server_log_reexports_central_logger(tmp_path):
    import server

    log_path = tmp_path / "server.log"
    logger.init({
        "name": "test-app",
        "handlers": {"file": {"path": str(log_path)}},
        "format": "%(message)s",
    })
    server.log("via-server", level="warning", code=42)

    content = log_path.read_text()
    assert "via-server" in content
    assert "code=42" in content


def test_init_from_real_config_yaml_shape(tmp_path):
    """Ensure the exact keys in config.yaml are consumed by logger.init."""
    log_path = tmp_path / "from-yaml.log"
    config = {
        "name": "app",
        "level": "info",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "handlers": {
            "console": {},
            "file": {"path": str(log_path)},
        },
    }

    # Round-trip through YAML like server.load_config does.
    loaded = yaml.safe_load(yaml.dump(config))
    logger.init(loaded)
    logger.info("from-config")

    line = log_path.read_text().strip()
    assert " - app - INFO - from-config" in line
    assert logger.get_logger().name == "app"
    handler_types = {type(h).__name__ for h in logger.get_logger().handlers}
    assert handler_types == {"StreamHandler", "FileHandler"}
