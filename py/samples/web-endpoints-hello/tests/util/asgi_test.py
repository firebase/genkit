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

"""Tests for src.util.asgi — low-level ASGI helpers.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/util/asgi_test.py -v
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.util.asgi import (
    FALLBACK_IP,
    get_client_ip,
    get_content_length,
    get_header,
    send_json_error,
)


def _http_scope(
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] = ("127.0.0.1", 12345),
) -> dict[str, Any]:
    """Build a minimal ASGI HTTP scope for testing."""
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/test",
        "scheme": "http",
        "headers": headers or [],
        "client": client,
    }


class _ResponseCapture:
    """Captures ASGI send messages for test assertions."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        """Record an ASGI message."""
        self.messages.append(message)

    @property
    def status(self) -> int | None:
        """Return the HTTP status code from the response start message."""
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return msg["status"]
        return None

    @property
    def headers(self) -> dict[str, str]:
        """Return decoded response headers as a dict."""
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return {name.decode(): value.decode() for name, value in msg.get("headers", [])}
        return {}

    @property
    def body(self) -> bytes:
        """Return the response body bytes."""
        for msg in self.messages:
            if msg["type"] == "http.response.body":
                return msg.get("body", b"")
        return b""


class TestSendJsonError:
    """Tests for `send_json_error`."""

    @pytest.mark.asyncio
    async def test_sends_status_code(self) -> None:
        """Verify the response status code matches the given code."""
        capture = _ResponseCapture()
        await send_json_error(capture, 413, "Payload Too Large", "Body exceeds limit")
        assert capture.status == 413

    @pytest.mark.asyncio
    async def test_sends_json_body(self) -> None:
        """Verify the response body contains error and detail fields."""
        capture = _ResponseCapture()
        await send_json_error(capture, 429, "Too Many Requests", "Slow down")
        body = json.loads(capture.body)
        assert body["error"] == "Too Many Requests"
        assert body["detail"] == "Slow down"

    @pytest.mark.asyncio
    async def test_content_type_is_json(self) -> None:
        """Verify the content-type header is application/json."""
        capture = _ResponseCapture()
        await send_json_error(capture, 500, "Error", "Oops")
        assert capture.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_content_length_is_correct(self) -> None:
        """Verify content-length matches the serialized body size."""
        capture = _ResponseCapture()
        await send_json_error(capture, 400, "Bad Request", "Invalid")
        expected_len = len(json.dumps({"error": "Bad Request", "detail": "Invalid"}).encode())
        assert capture.headers["content-length"] == str(expected_len)

    @pytest.mark.asyncio
    async def test_extra_headers_included(self) -> None:
        """Verify extra headers are included in the response."""
        capture = _ResponseCapture()
        await send_json_error(
            capture,
            429,
            "Rate Limited",
            "Wait",
            extra_headers=[(b"retry-after", b"5")],
        )
        assert capture.headers["retry-after"] == "5"

    @pytest.mark.asyncio
    async def test_no_extra_headers(self) -> None:
        """Verify response omits extra headers when none are given."""
        capture = _ResponseCapture()
        await send_json_error(capture, 404, "Not Found", "Gone")
        assert "retry-after" not in capture.headers

    @pytest.mark.asyncio
    async def test_sends_two_messages(self) -> None:
        """Verify send_json_error emits exactly two ASGI messages."""
        capture = _ResponseCapture()
        await send_json_error(capture, 500, "Error", "Oops")
        assert len(capture.messages) == 2
        assert capture.messages[0]["type"] == "http.response.start"
        assert capture.messages[1]["type"] == "http.response.body"


class TestGetClientIp:
    """Tests for `get_client_ip`."""

    def test_with_client_tuple(self) -> None:
        """Verify IP is extracted from the client tuple."""
        scope = _http_scope(client=("10.0.0.1", 5000))
        assert get_client_ip(scope) == "10.0.0.1"

    def test_without_client(self) -> None:
        """Verify fallback IP when client key is missing."""
        scope = _http_scope()
        del scope["client"]
        assert get_client_ip(scope) == FALLBACK_IP

    def test_with_none_client(self) -> None:
        """Verify fallback IP when client is None."""
        scope = _http_scope()
        scope["client"] = None
        assert get_client_ip(scope) == FALLBACK_IP

    def test_ipv6(self) -> None:
        """Verify IPv6 loopback address is returned correctly."""
        scope = _http_scope(client=("::1", 5000))
        assert get_client_ip(scope) == "::1"


class TestGetHeader:
    """Tests for `get_header`."""

    def test_found(self) -> None:
        """Verify header value is returned when present."""
        scope = _http_scope(
            headers=[
                (b"x-request-id", b"abc123"),
                (b"content-type", b"application/json"),
            ]
        )
        assert get_header(scope, b"x-request-id") == "abc123"

    def test_not_found(self) -> None:
        """Verify None is returned for a missing header."""
        scope = _http_scope(headers=[(b"content-type", b"text/plain")])
        assert get_header(scope, b"x-request-id") is None

    def test_empty_headers(self) -> None:
        """Verify None is returned when headers list is empty."""
        scope = _http_scope(headers=[])
        assert get_header(scope, b"x-request-id") is None

    def test_no_headers_key(self) -> None:
        """Verify None is returned when scope has no headers key."""
        scope = {"type": "http"}
        assert get_header(scope, b"x-request-id") is None

    def test_returns_first_match(self) -> None:
        """Verify only the first matching header value is returned."""
        scope = _http_scope(
            headers=[
                (b"x-custom", b"first"),
                (b"x-custom", b"second"),
            ]
        )
        assert get_header(scope, b"x-custom") == "first"

    def test_latin1_decoding(self) -> None:
        """Verify header values are decoded as latin-1."""
        scope = _http_scope(
            headers=[
                (b"x-custom", "caf\u00e9".encode("latin-1")),
            ]
        )
        assert get_header(scope, b"x-custom") == "caf\u00e9"


class TestGetContentLength:
    """Tests for `get_content_length`."""

    def test_valid_content_length(self) -> None:
        """Verify a valid content-length is returned as int."""
        scope = _http_scope(headers=[(b"content-length", b"1024")])
        assert get_content_length(scope) == 1024

    def test_zero(self) -> None:
        """Verify zero content-length is returned as 0."""
        scope = _http_scope(headers=[(b"content-length", b"0")])
        assert get_content_length(scope) == 0

    def test_missing(self) -> None:
        """Verify None is returned when content-length is absent."""
        scope = _http_scope(headers=[])
        assert get_content_length(scope) is None

    def test_invalid(self) -> None:
        """Verify None is returned for non-numeric content-length."""
        scope = _http_scope(headers=[(b"content-length", b"not-a-number")])
        assert get_content_length(scope) is None

    def test_empty_value(self) -> None:
        """Verify None is returned for empty content-length value."""
        scope = _http_scope(headers=[(b"content-length", b"")])
        assert get_content_length(scope) is None
