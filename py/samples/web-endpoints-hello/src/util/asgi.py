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

"""Low-level ASGI response helpers and header extraction.

Pure-ASGI utilities with no framework dependency (no FastAPI, Litestar,
or Quart imports). Used by the security, rate-limit, and request-ID
middleware.

- :func:`send_json_error` — Send a JSON error response with arbitrary
  status code and optional extra headers.
- :func:`get_client_ip` — Extract the client IP from an ASGI scope.
- :func:`get_header` — Extract a single header value from an ASGI scope.
- :func:`get_content_length` — Extract Content-Length as an ``int | None``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Receive = Callable[..., Any]
Send = Callable[..., Any]
ASGIApp = Callable[..., Any]

Headers = list[tuple[bytes, bytes]]
"""Type alias for ASGI header lists."""

FALLBACK_IP = "0.0.0.0"  # noqa: S104 — used when client tuple is missing


async def send_json_error(
    send: Send,
    status: int,
    title: str,
    detail: str,
    extra_headers: Headers | None = None,
) -> None:
    """Send a JSON error response over an ASGI ``send`` callable.

    Constructs a minimal ``{"error": ..., "detail": ...}`` body and
    sends it as a complete HTTP response.

    Args:
        send: The ASGI send callable.
        status: HTTP status code (e.g. 413, 429, 503).
        title: Short error title (e.g. ``"Too Many Requests"``).
        detail: Human-readable detail message.
        extra_headers: Optional additional response headers
            (e.g. ``[(b'retry-after', b'5')]``).
    """
    body = json.dumps({"error": title, "detail": detail}).encode()
    headers: Headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": headers,
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


def get_client_ip(scope: Scope) -> str:
    """Extract the client IP address from an ASGI scope.

    Falls back to ``'0.0.0.0'`` if the ``client`` tuple is missing
    (e.g. in test environments or Unix-socket connections).

    Args:
        scope: The ASGI connection scope.

    Returns:
        Client IP address string.
    """
    client = scope.get("client")
    return client[0] if client else FALLBACK_IP


def get_header(scope: Scope, name: bytes) -> str | None:
    """Extract a single header value from an ASGI scope.

    Scans the ``headers`` list in the scope for the first header
    matching ``name`` (case-sensitive, already lowercased in ASGI).

    Args:
        scope: The ASGI connection scope.
        name: Header name as lowercase bytes (e.g. ``b'x-request-id'``).

    Returns:
        The header value as a ``str``, or ``None`` if not found.
    """
    for header_name, header_value in scope.get("headers", []):
        if header_name == name:
            return header_value.decode("latin-1")
    return None


def get_content_length(scope: Scope) -> int | None:
    """Extract the Content-Length header as an integer.

    Args:
        scope: The ASGI connection scope.

    Returns:
        The content length in bytes, or ``None`` if the header is
        missing or unparsable.
    """
    raw = get_header(scope, b"content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None
