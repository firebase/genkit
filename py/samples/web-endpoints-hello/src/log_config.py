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

"""Logging setup for development and production.

Configures Rich tracebacks and structlog + stdlib logging. Two modes:

- **console** (default) — Colored, human-readable output for local dev.
- **json** — Machine-parseable JSON lines for production log
  aggregators (Cloud Logging, ELK, Datadog, etc.).

The format is selected via the ``LOG_FORMAT`` environment variable::

    LOG_FORMAT=json python -m src       # JSON output
    LOG_FORMAT=console python -m src    # colored console (default)
    python -m src                       # colored console (default)

Usage::

    from src.log_config import setup_logging

    setup_logging()  # Call once at startup.
"""

import logging
import os
import re
import sys

import structlog
import structlog.types
from rich.traceback import install as _install_rich_traceback

# Patterns that look like API keys or tokens.  We redact the middle of
# any value that matches, preserving the first 4 and last 2 characters
# so the key can still be identified in logs without being usable.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization|credential)"),
)
_SECRET_FIELD_NAMES: frozenset[str] = frozenset({
    "api_key",
    "apikey",
    "api-key",
    "gemini_api_key",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "credential",
    "credentials",
    "sentry_dsn",
    "dsn",
})


def _mask_value(value: str) -> str:
    """Mask a secret value, keeping the first 4 and last 2 characters."""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * (len(value) - 6)}{value[-2:]}"


def _redact_secrets(
    _logger: structlog.types.WrappedLogger,
    _method: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Structlog processor that redacts secret values from log events.

    Checks every key in the event dict against known secret field names
    and patterns.  Values that match are masked (e.g. ``AIza****Qw``).
    """
    for key in list(event_dict.keys()):
        if not isinstance(event_dict[key], str):
            continue
        lower_key = key.lower().replace("-", "_")
        if lower_key in _SECRET_FIELD_NAMES:
            event_dict[key] = _mask_value(event_dict[key])
            continue
        for pattern in _SECRET_PATTERNS:
            if pattern.search(lower_key):
                event_dict[key] = _mask_value(event_dict[key])
                break
    return event_dict


def _want_json() -> bool:
    """Return True when JSON log output is requested.

    Set ``LOG_FORMAT=json`` in production environments (Cloud Run,
    Kubernetes, etc.) so logs are machine-parseable.
    """
    return os.environ.get("LOG_FORMAT", "").lower() == "json"


def _want_colors() -> bool:
    """Decide whether to emit ANSI color codes.

    Color is enabled unless explicitly suppressed via ``NO_COLOR=1``
    (see https://no-color.org).  We default to **True** rather than
    checking ``isatty()`` because ``genkit start`` pipes
    stdout/stderr through the dev-server, which makes ``isatty()``
    return ``False`` even though the output ultimately lands in a
    color-capable terminal or the Dev UI.
    """
    return not os.environ.get("NO_COLOR", "")


def setup_logging(log_level: int = logging.DEBUG) -> None:
    """One-stop logging setup for dev and production.

    Installs Rich tracebacks and configures *both* structlog and
    Python's standard ``logging`` module. Output format depends on
    the ``LOG_FORMAT`` environment variable:

    - ``LOG_FORMAT=json`` — JSON lines (one object per log event)
      suitable for Cloud Logging, ELK, Datadog, etc. Each line
      includes ``timestamp``, ``level``, ``logger``, ``event``, and
      any bound context (e.g. ``request_id``).
    - ``LOG_FORMAT=console`` or unset — colored human-readable output.

    Call this once at startup before any logging calls.

    Args:
        log_level: Minimum log level to display.  Defaults to
            ``logging.DEBUG``.
    """
    use_json = _want_json()

    if not use_json:
        _install_rich_traceback(show_locals=True, width=120, extra_lines=3)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _redact_secrets,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if use_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=_want_colors())

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy OTel exporter / urllib3 loggers.  When Jaeger or
    # another OTLP collector is not running, these libraries emit
    # enormous multi-page tracebacks (ConnectionRefusedError) at
    # WARNING/ERROR level on every export attempt, drowning out actual
    # application output.  Raising their level to CRITICAL keeps the
    # console clean while still surfacing truly fatal issues.
    for noisy_logger in (
        "urllib3.connectionpool",
        "opentelemetry.exporter.otlp.proto.http",
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
        "opentelemetry.exporter.otlp.proto.grpc",
        "opentelemetry.sdk.trace.export",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)
