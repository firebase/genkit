# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Typed logging utilities for Genkit.

This module provides a typed wrapper around structlog to eliminate type warnings
and improve IDE support. The `Logger` protocol defines the interface used
throughout Genkit, and `get_logger()` returns a properly typed logger instance.

Usage:
    from genkit.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Server started", port=8080)
    await logger.ainfo("Async operation complete")
"""

from typing import Protocol

import structlog


class Logger(Protocol):
    """Protocol defining the logger interface used throughout Genkit.

    This protocol matches structlog's BoundLogger interface, providing type hints
    for all standard logging methods including async variants.
    """

    # Synchronous logging methods
    def debug(self, event: str | None = None, **kw: object) -> None:
        """Log a debug message."""
        ...

    def info(self, event: str | None = None, **kw: object) -> None:
        """Log an info message."""
        ...

    def warning(self, event: str | None = None, **kw: object) -> None:
        """Log a warning message."""
        ...

    def warn(self, event: str | None = None, **kw: object) -> None:
        """Log a warning message (alias for warning)."""
        ...

    def error(self, event: str | None = None, **kw: object) -> None:
        """Log an error message."""
        ...

    def exception(self, event: str | None = None, **kw: object) -> None:
        """Log an exception with traceback."""
        ...

    def critical(self, event: str | None = None, **kw: object) -> None:
        """Log a critical message."""
        ...

    def fatal(self, event: str | None = None, **kw: object) -> None:
        """Log a fatal message (alias for critical)."""
        ...

    # Async logging methods
    async def adebug(self, event: str | None = None, **kw: object) -> None:
        """Log a debug message asynchronously."""
        ...

    async def ainfo(self, event: str | None = None, **kw: object) -> None:
        """Log an info message asynchronously."""
        ...

    async def awarning(self, event: str | None = None, **kw: object) -> None:
        """Log a warning message asynchronously."""
        ...

    async def awarn(self, event: str | None = None, **kw: object) -> None:
        """Log a warning message asynchronously (alias for awarning)."""
        ...

    async def aerror(self, event: str | None = None, **kw: object) -> None:
        """Log an error message asynchronously."""
        ...

    async def aexception(self, event: str | None = None, **kw: object) -> None:
        """Log an exception with traceback asynchronously."""
        ...

    async def acritical(self, event: str | None = None, **kw: object) -> None:
        """Log a critical message asynchronously."""
        ...

    async def afatal(self, event: str | None = None, **kw: object) -> None:
        """Log a fatal message asynchronously (alias for acritical)."""
        ...

    # Context binding
    def bind(self, **new_values: object) -> 'Logger':
        """Return a new logger with bound context values."""
        ...

    def unbind(self, *keys: str) -> 'Logger':
        """Return a new logger with specified keys removed from context."""
        ...

    def try_unbind(self, *keys: str) -> 'Logger':
        """Return a new logger with specified keys removed (ignoring missing)."""
        ...

    def new(self, **new_values: object) -> 'Logger':
        """Return a new logger with only the specified context values."""
        ...


def get_logger(name: str | None = None) -> Logger:
    """Get a typed logger instance.

    This is a typed wrapper around structlog.get_logger() that provides
    proper type hints for IDE support and type checking.

    Args:
        name: Optional logger name (typically __name__).

    Returns:
        A typed logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info('Server started', port=8080)
        >>> await logger.ainfo('Async operation complete')
    """
    # The cast is safe because structlog's BoundLogger implements these methods
    return structlog.get_logger(name)
