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

"""Optional Sentry error tracking integration.

Initializes the Sentry SDK **only** when the ``SENTRY_DSN`` environment
variable (or config field) is set. When the DSN is empty, this module
is a complete no-op with zero runtime overhead.

Sentry provides:

- **Error reporting** — uncaught exceptions are captured and sent to
  Sentry with full stack traces, request context, and breadcrumbs.
- **Performance monitoring** — configurable sampling of transactions
  for latency tracking and bottleneck detection.
- **Framework integration** — auto-detects the active ASGI framework
  (FastAPI, Litestar, or Quart) and the gRPC server to enable
  framework-specific context enrichment.

Usage::

    from src.sentry_init import setup_sentry

    # Called early in main(), before app creation:
    setup_sentry(
        dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        framework="fastapi",
        environment="production",
        traces_sample_rate=0.1,
    )
"""

from __future__ import annotations

import typing

import structlog

if typing.TYPE_CHECKING:
    from sentry_sdk.integrations import Integration

logger = structlog.get_logger(__name__)


def setup_sentry(
    *,
    dsn: str,
    framework: str = "fastapi",
    environment: str = "",
    traces_sample_rate: float = 0.1,
    send_default_pii: bool = False,
) -> bool:
    """Initialize Sentry SDK with framework-specific integrations.

    This function is safe to call even if ``sentry-sdk`` is not installed;
    it will log a warning and return ``False``.

    Args:
        dsn: Sentry DSN (Data Source Name). Must be non-empty.
        framework: Active ASGI framework name (``fastapi``, ``litestar``,
            or ``quart``). Used to enable the matching integration.
        environment: Sentry environment tag (e.g. ``production``,
            ``staging``). Empty string omits the tag.
        traces_sample_rate: Fraction of transactions to sample for
            performance monitoring (0.0 to 1.0). Default: ``0.1``.
        send_default_pii: Whether to send Personally Identifiable
            Information (IP addresses, user agent, etc.). Default:
            ``False`` (PII stripped).

    Returns:
        ``True`` if Sentry was successfully initialized, ``False`` if
        the SDK is not installed or DSN is empty.
    """
    if not dsn:
        return False

    try:
        import sentry_sdk  # noqa: PLC0415 — sentry-sdk is an optional dependency
    except ImportError:
        logger.warning(
            "sentry-sdk not installed, skipping Sentry integration. "
            'Install with: pip install "sentry-sdk[fastapi,litestar,quart,grpc]"'
        )
        return False

    integrations = _build_integrations(framework)

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=send_default_pii,
        environment=environment or None,
    )

    logger.info(
        "Sentry initialized",
        framework=framework,
        environment=environment or "default",
        traces_sample_rate=traces_sample_rate,
        integrations=[type(i).__name__ for i in integrations],
    )
    return True


def _build_integrations(framework: str) -> list[Integration]:
    """Build the list of Sentry integrations for the given framework.

    Each integration is imported separately so missing extras don't
    prevent initialization of the ones that are available.

    Args:
        framework: Active ASGI framework name.

    Returns:
        List of Sentry integration instances.
    """
    integrations: list[Integration] = []

    if framework == "fastapi":
        try:
            from sentry_sdk.integrations.fastapi import (  # noqa: PLC0415 — optional Sentry integration
                FastApiIntegration,
            )

            integrations.append(FastApiIntegration())
        except ImportError:
            logger.debug("FastAPI Sentry integration not available")

    elif framework == "litestar":
        try:
            from sentry_sdk.integrations.litestar import (  # noqa: PLC0415 — optional Sentry integration
                LitestarIntegration,
            )

            integrations.append(LitestarIntegration())
        except ImportError:
            logger.debug("Litestar Sentry integration not available")

    elif framework == "quart":
        try:
            from sentry_sdk.integrations.quart import (  # noqa: PLC0415 — optional Sentry integration
                QuartIntegration,
            )

            integrations.append(QuartIntegration())
        except ImportError:
            logger.debug("Quart Sentry integration not available")

    # Always try gRPC integration (for the parallel gRPC server).
    try:
        from sentry_sdk.integrations.grpc import (  # noqa: PLC0415 — optional Sentry integration
            GRPCIntegration,
        )

        integrations.append(GRPCIntegration())
    except ImportError:
        logger.debug("gRPC Sentry integration not available")

    return integrations
