import logging

__logger : logging.Logger = None

def __get_level(level: str) -> int:
    return {
        "info": logging.INFO,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "debug": logging.DEBUG,
        "critical": logging.CRITICAL,
    }.get(level.lower(), logging.INFO)

def init(name: str, level: str = 'info', handlers: dict[str, dict] = {}):
    global __logger
    level = __get_level(level)

    __logger = logging.getLogger(name)
    __logger.setLevel(level=level)

    if 'console' in handlers:
        __logger.addHandler(logging.StreamHandler())
    if 'file' in handlers:
        __logger.addHandler(logging.FileHandler(handlers['file']['path']))

def log(message: str, level: str = "info"):
    global __logger
    level = __get_level(level)

    try:
        __logger.log(level=level, msg=message)
    except Exception as e:
        raise ValueError(f"Invalid level: {level}") from e
