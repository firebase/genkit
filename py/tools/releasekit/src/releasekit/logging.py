# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Structured logging for releasekit.

Configures `structlog <https://www.structlog.org/>`_ with two output modes:

- **Console** (default when TTY): Rich-colored, human-readable output.
- **JSON** (``--json-log``): Machine-readable, one JSON object per line.

Both modes write to stderr so stdout remains clean for piped output
(e.g., ``releasekit graph --format json | jq``).

Usage::

    from releasekit.logging import configure_logging, get_logger

    configure_logging(verbose=True, json_log=False)
    log = get_logger()
    log.info('discovered packages', count=21)
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    json_log: bool = False,
) -> None:
    """Configure structlog for releasekit.

    Should be called once at startup, before any logging calls.

    Args:
        verbose: Enable debug-level output.
        quiet: Suppress info-level output (only warnings and errors).
        json_log: Use JSON output instead of colored console output.
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure the standard library root logger so structlog can
    # forward events to it.
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stderr,
        level=level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_log:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=sys.stderr.isatty(),
        )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Install a ProcessorFormatter on all stdlib handlers so events
    # rendered by structlog look correct.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str = 'releasekit') -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger.

    Args:
        name: Logger name, used for filtering and identification.

    Returns:
        A :class:`structlog.stdlib.BoundLogger` instance.
    """
    return structlog.get_logger(name)


__all__ = [
    'configure_logging',
    'get_logger',
]
