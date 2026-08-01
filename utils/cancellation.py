"""Cooperative cancellation for streamed operations that spawn subprocesses.

A streamed build/package runs in a worker thread with a cancel token bound to
its context. The subprocess helpers (`utils.os.execute`, `ImageBuilder`) start
their children in a new session and register a watcher via `guard_process`, so
when the streaming request sees the client disconnect and sets the token, the
child process group is terminated and the operation unwinds.
"""

import os
import signal
import threading
import contextvars
from typing import Optional

_current_token: contextvars.ContextVar[Optional[threading.Event]] = contextvars.ContextVar(
    "labinat_cancel_token", default=None
)


class OperationCancelled(Exception):
    """Raised when an operation is aborted because its client went away."""


def current_token() -> Optional[threading.Event]:
    """The cancel token bound to the current context, or None."""
    return _current_token.get()


def bind_token(token: Optional[threading.Event]):
    """Bind `token` as the current context's cancel token; returns a reset handle."""
    return _current_token.set(token)


def reset_token(handle) -> None:
    _current_token.reset(handle)


def _terminate(proc) -> None:
    """Kill `proc`'s whole process group, falling back to the process itself."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except Exception:
            pass


def guard_process(proc, token: Optional[threading.Event] = None) -> Optional[threading.Thread]:
    """Watch `token` and terminate `proc`'s group if it is set while running.

    Returns the daemon watcher thread (or None when there is nothing to watch).
    The watcher polls the process so it exits on its own once the process ends.
    """
    token = token if token is not None else current_token()
    if token is None:
        return None

    def _watch():
        while proc.poll() is None:
            if token.wait(0.2):
                _terminate(proc)
                return

    watcher = threading.Thread(target=_watch, daemon=True)
    watcher.start()
    return watcher
