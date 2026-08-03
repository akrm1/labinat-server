"""Run a domain operation in the background and stream its logs over SSE.

Long operations (`build`, `package`, ...) run in a worker thread whose logging
output is routed into a per-thread queue and streamed to the client as
Server-Sent Events. If the client disconnects, the operation's cancel token is
set, which terminates any running subprocess (see `utils.cancellation`).
"""

import asyncio
import json
import logging
import queue
import threading
from typing import Any, Callable, Optional

from fastapi import Request
from fastapi.responses import StreamingResponse

from utils import logger as app_logger
from utils.cancellation import bind_token, reset_token, OperationCancelled

# Worker thread ident -> the queue draining that operation's log records.
_registry: dict[int, "queue.Queue[str]"] = {}
# Cancel tokens of every operation currently running, so a shutdown can collapse
# them all at once (terminating any subprocess they spawned).
_active_tokens: set[threading.Event] = set()
_registry_lock = threading.Lock()


class _RoutingHandler(logging.Handler):
    """Route each log record to the queue registered for its emitting thread."""

    def emit(self, record: logging.LogRecord) -> None:
        target = _registry.get(record.thread)
        if target is None:
            return
        try:
            target.put_nowait(self.format(record))
        except Exception:
            pass


_handler = _RoutingHandler()
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))


def _ensure_handler() -> None:
    """Make sure the routing handler is attached and DEBUG records reach it.

    The existing console/file handlers keep their configured level, so lowering
    the logger to DEBUG only feeds the routing handler (which captures shell
    output logged at debug) without flooding the normal sinks. Re-checked each
    call so a logger re-init (which clears handlers) does not drop it.
    """
    logger = app_logger.get_logger()
    if _handler not in logger.handlers:
        logger.addHandler(_handler)
    if logger.level == logging.NOTSET or logger.level > logging.DEBUG:
        logger.setLevel(logging.DEBUG)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_operation(
    request: Request,
    operation: Callable[[], Any],
    result_serializer: Optional[Callable[[Any], Any]] = None,
) -> StreamingResponse:
    """Return an SSE response that runs `operation` and streams its logs live.

    Emits `start`, then a `log` event per line, then a terminal `completed`,
    `error`, or `cancelled` event. A client disconnect cancels the operation.
    """
    _ensure_handler()

    log_queue: "queue.Queue[str]" = queue.Queue()
    cancel = threading.Event()
    done = threading.Event()
    outcome: dict[str, Any] = {}

    def worker() -> None:
        ident = threading.get_ident()
        with _registry_lock:
            _registry[ident] = log_queue
            _active_tokens.add(cancel)
        handle = bind_token(cancel)
        try:
            result = operation()
            outcome["status"] = "completed"
            outcome["result"] = result_serializer(result) if result_serializer else result
        except OperationCancelled:
            outcome["status"] = "cancelled"
        except Exception as error:  # surface any domain failure to the client
            outcome["status"] = "error"
            outcome["error"] = str(error)
        finally:
            reset_token(handle)
            with _registry_lock:
                _registry.pop(ident, None)
                _active_tokens.discard(cancel)
            done.set()

    worker_thread = threading.Thread(target=worker, daemon=True)

    async def event_generator():
        worker_thread.start()
        yield _sse("start", {"message": "operation started"})
        try:
            while True:
                if await request.is_disconnected():
                    cancel.set()
                    break

                drained = _drain(log_queue)
                for line in drained:
                    yield _sse("log", {"line": line})

                if done.is_set() and log_queue.empty():
                    break
                if not drained:
                    await asyncio.sleep(0.1)

            for line in _drain(log_queue):
                yield _sse("log", {"line": line})

            if cancel.is_set():
                done.wait(timeout=5)
                yield _sse("cancelled", {"message": "operation cancelled"})
            else:
                status = outcome.get("status", "completed")
                payload = {key: value for key, value in outcome.items() if key != "status"}
                yield _sse(status, payload)
        finally:
            # If the generator is closed early (client vanished), make sure the
            # worker is told to unwind rather than left running a subprocess.
            cancel.set()
            done.wait(timeout=5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _drain(log_queue: "queue.Queue[str]") -> list[str]:
    lines: list[str] = []
    try:
        while True:
            lines.append(log_queue.get_nowait())
    except queue.Empty:
        pass
    return lines


def collapse() -> int:
    """Cancel every in-flight operation and return how many were signalled.

    Setting each cancel token trips the subprocess guards, so any running
    build/package child process group is terminated. Used on server shutdown to
    avoid leaving orphaned processes behind.
    """
    with _registry_lock:
        tokens = list(_active_tokens)
    for token in tokens:
        token.set()
    return len(tokens)
