"""Centralized application logging.

All domain code should log through this module (or `server.log`, which is a
thin re-export). Configure once via `init()` from `config.yaml` during
`server.init()`.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

__logger: Optional[logging.Logger] = None

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def __get_level(level: str) -> int:
    return _LEVELS.get((level or "info").lower(), logging.INFO)


def is_initialized() -> bool:
    return __logger is not None


def get_logger() -> logging.Logger:
    """Return the process logger, creating a stderr fallback if not yet init'd.

    Domain modules may log before `server.init()` (e.g. in unit tests). A
    fallback avoids hard crashes while still emitting somewhere visible.
    """
    global __logger
    if __logger is None:
        fallback = logging.getLogger("labinat.uninitialized")
        if not fallback.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))
            fallback.addHandler(handler)
            fallback.setLevel(logging.INFO)
            fallback.propagate = False
        return fallback
    return __logger


def init(logger_config: Optional[dict] = None) -> logging.Logger:
    """Initialize (or reinitialize) the process-wide application logger.

    Expects the full `logger` section from `config.yaml`, e.g.::

        {
            "name": "app",
            "level": "info",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "handlers": {
                "console": {},
                "file": {"path": "app.log"},
            },
        }

    All supported keys are read here. Re-init clears previous handlers so
    tests and reloads do not stack duplicate handlers.
    """
    global __logger
    logger_config = dict(logger_config or {})

    name = logger_config.get("name", "app")
    level = logger_config.get("level", "info")
    log_format = logger_config.get("format", _DEFAULT_FORMAT)
    datefmt = logger_config.get("datefmt", _DEFAULT_DATEFMT)
    handlers = logger_config.get("handlers") or {}

    logger = logging.getLogger(name)
    logger.setLevel(__get_level(level))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(fmt=log_format, datefmt=datefmt)

    if "console" in handlers:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(__get_level(level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if "file" in handlers:
        file_cfg = handlers["file"] or {}
        path = file_cfg.get("path", "app.log")
        file_handler = logging.FileHandler(path)
        file_handler.setLevel(__get_level(level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # If no handlers were configured, still attach a stderr console so
    # accidental silent loss of logs does not happen in misconfigured envs.
    if not logger.handlers:
        fallback = logging.StreamHandler(sys.stderr)
        fallback.setLevel(__get_level(level))
        fallback.setFormatter(formatter)
        logger.addHandler(fallback)

    __logger = logger
    return logger


def log(message: str, level: str = "info", **extra: Any) -> None:
    """Log `message` at `level`.

    Optional keyword args are appended as `key=value` pairs for quick context
    without requiring a custom Formatter.
    """
    logger = get_logger()
    if extra:
        details = " ".join(f"{key}={value!r}" for key, value in extra.items())
        message = f"{message} | {details}"
    logger.log(__get_level(level), message)


def debug(message: str, **extra: Any) -> None:
    log(message, level="debug", **extra)


def info(message: str, **extra: Any) -> None:
    log(message, level="info", **extra)


def warning(message: str, **extra: Any) -> None:
    log(message, level="warning", **extra)


def error(message: str, **extra: Any) -> None:
    log(message, level="error", **extra)


def critical(message: str, **extra: Any) -> None:
    log(message, level="critical", **extra)


def reset() -> None:
    """Tear down the process logger (for tests)."""
    global __logger
    if __logger is not None:
        __logger.handlers.clear()
    __logger = None
