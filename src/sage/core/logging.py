"""Logging configuration for SAGE."""

import logging
import sys
from typing import Optional

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a configured logger for the given module name.

    Args:
        name: Logger name, typically __name__ from the calling module
        level: Optional log level override (defaults to settings.log_level)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(handler)

    if level is not None:
        logger.setLevel(level)

    return logger


def configure_logging(level: Optional[int] = None, quiet: bool = False) -> None:
    """Configure root logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). If None, uses settings.
        quiet: If True, only show warnings and errors
    """
    if level is None:
        from .config import settings
        level = settings.log_level_int

    if quiet:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stderr,
    )

    # Reduce noise from httpx (used by openai)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
