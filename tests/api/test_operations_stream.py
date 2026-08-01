"""The SSE operation runner: log streaming, completion, and disconnect-cancel."""

import asyncio
import threading

from app.api import operations
from utils import logger
from utils.cancellation import current_token


class FakeRequest:
    """Minimal stand-in for a Starlette Request's disconnect polling."""

    def __init__(self, disconnect_after=None):
        self._polls = 0
        self._disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._polls += 1
        if self._disconnect_after is None:
            return False
        return self._polls > self._disconnect_after


async def _collect(response) -> str:
    parts = []
    async for chunk in response.body_iterator:
        parts.append(chunk if isinstance(chunk, str) else chunk.decode())
    return "".join(parts)


def _init_logger():
    logger.init({"name": "test-stream", "level": "debug", "handlers": {"console": {}}})


def test_stream_reports_logs_then_completion():
    _init_logger()

    def operation():
        logger.info("hello from the operation")
        return {"ok": True}

    response = operations.stream_operation(FakeRequest(), operation, result_serializer=lambda r: r)
    body = asyncio.run(_collect(response))

    assert "event: start" in body
    assert "event: log" in body
    assert "hello from the operation" in body
    assert "event: completed" in body
    logger.reset()


def test_operation_failure_is_reported_as_error():
    _init_logger()

    def operation():
        raise RuntimeError("boom")

    response = operations.stream_operation(FakeRequest(), operation)
    body = asyncio.run(_collect(response))

    assert "event: error" in body
    assert "boom" in body
    logger.reset()


def test_client_disconnect_cancels_the_operation():
    _init_logger()
    observed = {}

    def operation():
        token = current_token()
        observed["had_token"] = token is not None
        # Block until the disconnect flips the cancel token.
        observed["was_cancelled"] = token.wait(timeout=5)
        return "should-not-matter"

    response = operations.stream_operation(FakeRequest(disconnect_after=0), operation)
    body = asyncio.run(_collect(response))

    assert observed["had_token"] is True
    assert observed["was_cancelled"] is True
    assert "event: cancelled" in body
    logger.reset()
