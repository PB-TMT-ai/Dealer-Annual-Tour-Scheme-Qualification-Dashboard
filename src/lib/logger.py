import os
import logging
from typing import Any

_is_dev = os.getenv("APP_ENV", "development") == "development"

logging.basicConfig(
    level=logging.DEBUG if _is_dev else logging.INFO,
    format="[%(levelname)s] %(message)s",
)

_logger = logging.getLogger("app")


def info(msg: str, data: Any = None) -> None:
    _logger.info(f"{msg} {data}" if data else msg)


def warn(msg: str, data: Any = None) -> None:
    _logger.warning(f"{msg} {data}" if data else msg)


def error(msg: str, err: Any = None) -> None:
    _logger.error(f"{msg} {err}" if err else msg)


def debug(msg: str, data: Any = None) -> None:
    if _is_dev:
        _logger.debug(f"{msg} {data}" if data else msg)
