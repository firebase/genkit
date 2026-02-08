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

"""Tests for ASGI server helpers.

Validates that serve_uvicorn, serve_granian, and serve_hypercorn
correctly configure and start their respective servers.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/server_test.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server import serve_granian, serve_hypercorn, serve_uvicorn


async def _noop_app(scope: dict, receive: object, send: object) -> None:
    """No-op ASGI app for server tests."""


@pytest.mark.asyncio
async def test_serve_uvicorn_configures_and_starts() -> None:
    """serve_uvicorn creates a Config and starts the server."""
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    with (
        patch("src.server.uvicorn.Config") as mock_config_cls,
        patch("src.server.uvicorn.Server", return_value=mock_server) as mock_server_cls,
    ):
        await serve_uvicorn(_noop_app, 8080, "info", 75)

    mock_config_cls.assert_called_once_with(
        _noop_app,
        host="0.0.0.0",  # noqa: S104 - verifying server binds to all interfaces
        port=8080,
        log_level="info",
        timeout_keep_alive=75,
    )
    mock_server_cls.assert_called_once()
    mock_server.serve.assert_awaited_once()


@pytest.mark.asyncio
async def test_serve_granian_configures_and_starts() -> None:
    """serve_granian creates an embedded Server and starts it."""
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    with (
        patch("granian.server.embed.Server", return_value=mock_server) as mock_cls,
        patch("granian.constants.Interfaces"),
        patch("granian.http.HTTP1Settings"),
    ):
        await serve_granian(_noop_app, 9090, "debug", 75)

    mock_cls.assert_called_once()
    mock_server.serve.assert_awaited_once()


@pytest.mark.asyncio
async def test_serve_hypercorn_configures_and_starts() -> None:
    """serve_hypercorn creates a Config and calls serve()."""
    mock_serve = AsyncMock()

    with (
        patch("hypercorn.asyncio.serve", mock_serve),
        patch("hypercorn.config.Config") as mock_config_cls,
    ):
        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config
        await serve_hypercorn(_noop_app, 7070, "warning", 90)

    mock_serve.assert_awaited_once()
    assert mock_config.keep_alive_timeout == 90


@pytest.mark.asyncio
async def test_serve_granian_missing_raises_system_exit() -> None:
    """serve_granian raises SystemExit when granian is not installed."""
    with patch.dict(
        "sys.modules", {"granian": None, "granian.constants": None, "granian.http": None, "granian.server.embed": None}
    ):
        with patch("builtins.__import__", side_effect=ImportError("No module named 'granian'")):
            with pytest.raises(SystemExit):
                await serve_granian(_noop_app, 8080, "info")
