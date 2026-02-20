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

"""Tests for optional Sentry integration.

Covers setup_sentry() initialization, framework auto-detection, and
graceful degradation when sentry-sdk is not installed.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/sentry_init_test.py -v
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

from src import sentry_init
from src.sentry_init import _build_integrations, setup_sentry  # noqa: PLC2701 — testing internal helper


def test_module_importable_without_sentry_sdk() -> None:
    """Regression: sentry_init must load when sentry-sdk is absent.

    The TYPE_CHECKING guard on the ``Integration`` import means the
    module should reload cleanly even when ``sentry_sdk`` is not
    installed.  This test prevents a future change from accidentally
    moving that import back to the top level.
    """
    with patch.dict(sys.modules, {"sentry_sdk": None, "sentry_sdk.integrations": None}):
        importlib.reload(sentry_init)


def test_setup_sentry_empty_dsn_returns_false() -> None:
    """setup_sentry returns False when DSN is empty."""
    result = setup_sentry(dsn="")
    assert result is False


def test_setup_sentry_missing_sdk_returns_false() -> None:
    """setup_sentry returns False when sentry-sdk is not installed."""
    with patch.dict(sys.modules, {"sentry_sdk": None}):
        result = setup_sentry(dsn="https://examplePublicKey@o0.ingest.sentry.io/0")
    assert result is False


def test_setup_sentry_initializes_with_valid_dsn() -> None:
    """setup_sentry calls sentry_sdk.init when DSN is provided."""
    mock_sdk = MagicMock()
    with patch.dict(sys.modules, {"sentry_sdk": mock_sdk}):
        result = setup_sentry(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            framework="fastapi",
            environment="test",
            traces_sample_rate=0.5,
        )

    assert result is True
    mock_sdk.init.assert_called_once()
    call_kwargs = mock_sdk.init.call_args
    assert call_kwargs[1]["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
    assert call_kwargs[1]["traces_sample_rate"] == 0.5
    assert call_kwargs[1]["environment"] == "test"
    assert call_kwargs[1]["send_default_pii"] is False


def test_setup_sentry_omits_environment_when_empty() -> None:
    """setup_sentry passes environment=None when it's empty."""
    mock_sdk = MagicMock()
    with patch.dict(sys.modules, {"sentry_sdk": mock_sdk}):
        setup_sentry(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            environment="",
        )

    call_kwargs = mock_sdk.init.call_args[1]
    assert call_kwargs["environment"] is None


def test_setup_sentry_pii_disabled_by_default() -> None:
    """PII is not sent by default."""
    mock_sdk = MagicMock()
    with patch.dict(sys.modules, {"sentry_sdk": mock_sdk}):
        setup_sentry(dsn="https://examplePublicKey@o0.ingest.sentry.io/0")

    call_kwargs = mock_sdk.init.call_args[1]
    assert call_kwargs["send_default_pii"] is False


def test_setup_sentry_pii_can_be_enabled() -> None:
    """PII can be explicitly enabled."""
    mock_sdk = MagicMock()
    with patch.dict(sys.modules, {"sentry_sdk": mock_sdk}):
        setup_sentry(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            send_default_pii=True,
        )

    call_kwargs = mock_sdk.init.call_args[1]
    assert call_kwargs["send_default_pii"] is True


def test_build_integrations_fastapi() -> None:
    """FastAPI framework produces FastApiIntegration."""
    mock_integration = MagicMock()
    mock_module = MagicMock()
    mock_module.FastApiIntegration = mock_integration
    with patch.dict(sys.modules, {"sentry_sdk.integrations.fastapi": mock_module}):
        integrations = _build_integrations("fastapi")

    assert len(integrations) >= 1
    mock_integration.assert_called_once()


def test_build_integrations_litestar() -> None:
    """Litestar framework produces LitestarIntegration."""
    mock_integration = MagicMock()
    mock_module = MagicMock()
    mock_module.LitestarIntegration = mock_integration
    with patch.dict(sys.modules, {"sentry_sdk.integrations.litestar": mock_module}):
        integrations = _build_integrations("litestar")

    assert len(integrations) >= 1
    mock_integration.assert_called_once()


def test_build_integrations_quart() -> None:
    """Quart framework produces QuartIntegration."""
    mock_integration = MagicMock()
    mock_module = MagicMock()
    mock_module.QuartIntegration = mock_integration
    with patch.dict(sys.modules, {"sentry_sdk.integrations.quart": mock_module}):
        integrations = _build_integrations("quart")

    assert len(integrations) >= 1
    mock_integration.assert_called_once()


def test_build_integrations_graceful_on_missing_extras() -> None:
    """Missing integration extras don't cause errors."""
    # Force all sentry modules to be missing.
    patches = {
        "sentry_sdk.integrations.fastapi": None,
        "sentry_sdk.integrations.grpc": None,
    }
    with patch.dict(sys.modules, patches):
        integrations = _build_integrations("fastapi")

    # Should return an empty list (no crash).
    assert isinstance(integrations, list)


def test_build_integrations_always_tries_grpc() -> None:
    """GRPC integration is always attempted regardless of framework."""
    mock_grpc_integration = MagicMock()
    mock_grpc_module = MagicMock()
    mock_grpc_module.GRPCIntegration = mock_grpc_integration

    # Block framework-specific integration, allow gRPC.
    patches = {
        "sentry_sdk.integrations.fastapi": None,
        "sentry_sdk.integrations.grpc": mock_grpc_module,
    }
    with patch.dict(sys.modules, patches):
        integrations = _build_integrations("fastapi")

    assert len(integrations) == 1
    mock_grpc_integration.assert_called_once()
