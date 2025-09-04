"""Logging configuration for the application."""

import logging
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import settings


def setup_logging() -> None:
    """Set up structured logging with Rich formatting."""
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                rich_tracebacks=True,
                markup=True,
                show_path=True,
            ),
        ],
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper()),
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, typically __name__

    Returns:
        Configured structlog logger

    """
    return structlog.get_logger(name)


class ContextLogger:
    """Context manager for adding context to all log messages."""

    def __init__(self, **context: Any) -> None:
        """Initialize with context to add to logs.

        Args:
            **context: Key-value pairs to add to log context

        """
        self.context = context

    def __enter__(self) -> None:
        """Enter context manager."""
        structlog.contextvars.bind_contextvars(**self.context)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """Log a function call with parameters.

    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log

    """
    logger = get_logger("function_calls")
    logger.info(
        "Function called",
        function=func_name,
        parameters={k: str(v)[:100] for k, v in kwargs.items()},
    )
