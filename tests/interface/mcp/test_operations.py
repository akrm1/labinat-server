"""Operation tools and their log capture."""

import logging

from app.interface.mcp.logs import capture_logs
from tests.interface.mcp.conftest import call_one
from utils import logger


def test_emit_on_empty_project_returns_no_files_with_logs(server):
    created = call_one(server, "create_project", name="demo")
    result = call_one(server, "emit", project_id=created["id"])

    assert result["status"] == "completed"
    assert result["result"] == []
    # The operation's own logging is captured and returned to the caller.
    joined = "\n".join(result["logs"])
    assert "Emitting project blocks" in joined
    assert "Emit finished" in joined


def test_capture_logs_collects_records_and_restores_level():
    logger.init({"name": "test-mcp", "level": "info", "handlers": {"console": {}}})
    log = logger.get_logger()
    before = log.level

    with capture_logs() as lines:
        logger.info("hello from inside")
        logger.debug("debug detail is captured too")

    assert any("hello from inside" in line for line in lines)
    assert any("debug detail is captured too" in line for line in lines)
    # Level is restored and the capture handler is detached afterwards.
    assert log.level == before
    assert all(not isinstance(h, logging.Handler) or h.__class__.__name__ != "_CollectingHandler" for h in log.handlers)

    logger.reset()
