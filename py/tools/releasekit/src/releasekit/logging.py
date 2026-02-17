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
import os
import sys
from typing import Any

import structlog


def configure_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    json_log: bool = False,
    redact_secrets: bool = True,
) -> None:
    """Configure structlog for releasekit.

    Should be called once at startup, before any logging calls.

    Args:
        verbose: Enable debug-level output.
        quiet: Suppress info-level output (only warnings and errors).
        json_log: Use JSON output instead of colored console output.
        redact_secrets: Scrub sensitive env var values from log output.
            Defaults to ``True``.  Set to ``False`` for local debugging
            when you need to see actual secret values.  Can also be
            disabled via the ``RELEASEKIT_REDACT_SECRETS=0`` env var.
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

    global _secret_values, _redaction_enabled  # noqa: PLW0603
    _redaction_enabled = (
        redact_secrets
        and os.environ.get(
            'RELEASEKIT_REDACT_SECRETS',
            '1',
        )
        != '0'
    )
    _secret_values = _build_secret_values() if _redaction_enabled else frozenset()

    shared_processors: list[structlog.types.Processor] = [  # type: ignore[assignment]
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        redact_sensitive_values,
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


# Env var names whose runtime values must never appear in logs.
_SENSITIVE_ENV_VARS: tuple[str, ...] = (
    'GEMINI_API_KEY',
    'GOOGLE_API_KEY',
    'GOOGLE_APPLICATION_CREDENTIALS',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'PYPI_TOKEN',
    'TESTPYPI_TOKEN',
    'UV_PUBLISH_TOKEN',
    'NPM_TOKEN',
    'GITHUB_TOKEN',
    'GH_TOKEN',
    'BITBUCKET_TOKEN',
    'BITBUCKET_APP_PASSWORD',
    'GITLAB_TOKEN',
    'AWS_SECRET_ACCESS_KEY',
    'CARGO_REGISTRY_TOKEN',
    'PUB_TOKEN',
    'MAVEN_GPG_PASSPHRASE',
)

_REDACTED = '[REDACTED]'


def _build_secret_values() -> frozenset[str]:
    """Collect current runtime values of sensitive env vars.

    Only non-empty values are included. The set is rebuilt on each
    call to ``configure_logging`` so tests can inject env vars.
    """
    values: set[str] = set()
    for name in _SENSITIVE_ENV_VARS:
        val = os.environ.get(name, '')
        if val:
            values.add(val)
    return frozenset(values)


# Populated by configure_logging(); used by the processor.
_secret_values: frozenset[str] = frozenset()
_redaction_enabled: bool = True


def _scrub(value: object) -> object:
    """Replace any secret substring in a string value with ``[REDACTED]``."""
    if not isinstance(value, str) or not _secret_values:
        return value
    result = value
    for secret in _secret_values:
        if len(secret) >= 8 and secret in result:
            result = result.replace(secret, _REDACTED)
    return result


def redact_sensitive_values(
    logger: Any,  # noqa: ANN401
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor: scrub secret values from all event fields.

    Replaces the runtime value of any sensitive environment variable
    (e.g. ``GEMINI_API_KEY``) with ``[REDACTED]`` in every string
    field of the log event dict. This is defense-in-depth — even if
    code accidentally passes a secret as a log kwarg, it gets
    scrubbed before output.
    """
    if not _secret_values:
        return event_dict
    return {k: _scrub(v) for k, v in event_dict.items()}


__all__ = [
    'configure_logging',
    'get_logger',
    'redact_sensitive_values',
]
