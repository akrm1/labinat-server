"""Capture the app logger's output for the duration of a tool call.

MCP tools are request/response, so long operations (`build`, `package`, ...) can't
stream. Instead we collect everything the operation logs — including subprocess
output logged at DEBUG — and hand it back with the result.

Capture is scoped to the calling thread: FastMCP runs each sync tool in its own
worker thread, and the operation (and its subprocesses) log from that same thread,
so filtering on the thread id keeps concurrent tool calls from bleeding together.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator, List

from utils import logger as app_logger


class _CollectingHandler(logging.Handler):
    """Append formatted records emitted by one thread into a list."""

    def __init__(self, thread_id: int, sink: List[str]) -> None:
        super().__init__(level=logging.DEBUG)
        self._thread_id = thread_id
        self._sink = sink
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self._thread_id:
            return
        try:
            self._sink.append(self.format(record))
        except Exception:
            pass


@contextmanager
def capture_logs() -> Iterator[List[str]]:
    """Collect this thread's log lines while the block runs.

    Lowers the logger to DEBUG so subprocess output reaches the handler, then
    restores the previous level and detaches the handler on exit.
    """
    logger = app_logger.get_logger()
    sink: List[str] = []
    handler = _CollectingHandler(threading.get_ident(), sink)

    previous_level = logger.level
    logger.addHandler(handler)
    if logger.level == logging.NOTSET or logger.level > logging.DEBUG:
        logger.setLevel(logging.DEBUG)

    try:
        yield sink
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
