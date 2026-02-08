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

"""Connection pooling and keep-alive tuning for outbound HTTP clients.

Production services make many outbound HTTP calls to LLM APIs. Without
proper connection management:

- **Connection churn** — A new TCP + TLS handshake per request adds
  ~50-200ms latency. With keep-alive, subsequent requests reuse the
  existing connection and skip the handshake entirely.
- **Timeouts** — No timeout on LLM calls means a degraded API can
  block a worker indefinitely. Explicit timeouts ensure requests
  fail predictably.
- **Pool exhaustion** — Too few connections cause requests to queue;
  too many waste memory and file descriptors.

This module provides:

- **make_http_options()** — Creates a ``google.genai.types.HttpOptions``
  with configurable timeout for the Google GenAI SDK.
- **configure_httpx_defaults()** — Sets environment variables that
  control httpx connection pool behavior (used by many Python SDKs).
- **KEEP_ALIVE_TIMEOUT** — Recommended keep-alive timeout for ASGI
  servers, tuned to avoid load balancer disconnect races.

Configuration via environment variables::

    LLM_TIMEOUT = 120000  # LLM API timeout in ms (default: 120000 = 2min)
    HTTPX_POOL_MAX = 100  # max connections per pool (default: 100)
    HTTPX_POOL_MAX_KEEPALIVE = 20  # max idle keep-alive connections (default: 20)
    KEEP_ALIVE_TIMEOUT = 75  # server keep-alive in seconds (default: 75)
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

KEEP_ALIVE_TIMEOUT: int = 75
"""Server-side keep-alive timeout in seconds.

Set to 75s — slightly above the default 60s load balancer idle
timeout used by Cloud Run, ALB, and Azure Front Door. This ensures
the server never closes a connection before the load balancer does,
avoiding sporadic 502 errors.
"""

LLM_TIMEOUT_MS: int = 120_000
"""Default timeout for LLM API calls in milliseconds (2 minutes).

LLM generation can take 10-60s for complex prompts. Two minutes
provides headroom for large context windows and tool-use chains
while still failing in a reasonable time if the API is stuck.
"""


def make_http_options(timeout_ms: int | None = None) -> dict[str, Any]:
    """Create HTTP options for the Google GenAI SDK.

    Returns a dict suitable for passing to ``google.genai.types.HttpOptions``
    with a configured timeout. The timeout prevents indefinite hangs
    when the Gemini API is degraded.

    Args:
        timeout_ms: Timeout in milliseconds. Default: ``LLM_TIMEOUT_MS``
            (120000 = 2 minutes). Override via ``LLM_TIMEOUT`` env var.

    Returns:
        A dict with ``timeout`` key (in milliseconds).
    """
    if timeout_ms is None:
        timeout_ms = int(os.environ.get("LLM_TIMEOUT", str(LLM_TIMEOUT_MS)))

    logger.info("LLM HTTP options configured", timeout_ms=timeout_ms)
    return {"timeout": timeout_ms}


def configure_httpx_defaults(
    *,
    pool_max: int = 100,
    pool_max_keepalive: int = 20,
) -> None:
    """Set environment variables that tune httpx connection pools.

    Many Python SDKs (including Google Cloud libraries) use httpx
    under the hood. These environment variables control pool sizing:

    - ``HTTPX_DEFAULT_MAX_CONNECTIONS`` — Maximum total connections
      across all hosts in the pool.
    - ``HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS`` — Maximum idle
      connections to keep alive in the pool.

    These values are sensible defaults for a single-process ASGI
    server handling moderate traffic. For multi-worker deployments,
    each worker maintains its own pool.

    Args:
        pool_max: Maximum total connections across all hosts in the
            pool.  Also reads from ``HTTPX_POOL_MAX`` env var.
        pool_max_keepalive: Maximum idle keep-alive connections in
            the pool.  Also reads from ``HTTPX_POOL_MAX_KEEPALIVE``
            env var.
    """
    max_str = os.environ.get("HTTPX_POOL_MAX", str(pool_max))
    keepalive_str = os.environ.get("HTTPX_POOL_MAX_KEEPALIVE", str(pool_max_keepalive))

    os.environ.setdefault("HTTPX_DEFAULT_MAX_CONNECTIONS", max_str)
    os.environ.setdefault("HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS", keepalive_str)

    logger.info(
        "httpx connection pool defaults configured",
        max_connections=max_str,
        max_keepalive=keepalive_str,
    )
