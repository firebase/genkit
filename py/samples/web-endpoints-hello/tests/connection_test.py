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

"""Tests for connection pooling and HTTP option helpers."""

import os

import pytest

from src.connection import (
    KEEP_ALIVE_TIMEOUT,
    LLM_TIMEOUT_MS,
    configure_httpx_defaults,
    make_http_options,
)


class TestMakeHttpOptions:
    """Tests for `make_http_options`."""

    def test_default_timeout(self) -> None:
        """Verify default timeout equals LLM_TIMEOUT_MS."""
        opts = make_http_options()
        assert opts["timeout"] == LLM_TIMEOUT_MS

    def test_custom_timeout(self) -> None:
        """Verify custom timeout_ms overrides the default."""
        opts = make_http_options(timeout_ms=60_000)
        assert opts["timeout"] == 60_000

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify LLM_TIMEOUT env var overrides the default."""
        monkeypatch.setenv("LLM_TIMEOUT", "90000")
        opts = make_http_options()
        assert opts["timeout"] == 90_000


class TestConfigureHttpxDefaults:
    """Tests for `configure_httpx_defaults`."""

    def test_sets_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify env vars are set to defaults when unset."""
        monkeypatch.delenv("HTTPX_DEFAULT_MAX_CONNECTIONS", raising=False)
        monkeypatch.delenv("HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS", raising=False)
        configure_httpx_defaults()
        assert os.environ.get("HTTPX_DEFAULT_MAX_CONNECTIONS") == "100"
        assert os.environ.get("HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS") == "20"

    def test_respects_existing_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify existing env vars are not overwritten."""
        monkeypatch.setenv("HTTPX_DEFAULT_MAX_CONNECTIONS", "50")
        configure_httpx_defaults()
        assert os.environ.get("HTTPX_DEFAULT_MAX_CONNECTIONS") == "50"

    def test_custom_pool_sizes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify HTTPX_POOL_MAX and HTTPX_POOL_MAX_KEEPALIVE are respected."""
        monkeypatch.delenv("HTTPX_DEFAULT_MAX_CONNECTIONS", raising=False)
        monkeypatch.delenv("HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS", raising=False)
        monkeypatch.setenv("HTTPX_POOL_MAX", "200")
        monkeypatch.setenv("HTTPX_POOL_MAX_KEEPALIVE", "50")
        configure_httpx_defaults()
        assert os.environ.get("HTTPX_DEFAULT_MAX_CONNECTIONS") == "200"
        assert os.environ.get("HTTPX_DEFAULT_MAX_KEEPALIVE_CONNECTIONS") == "50"


class TestConstants:
    """Tests for module-level constants."""

    def test_keep_alive_exceeds_lb_default(self) -> None:
        """Verify KEEP_ALIVE_TIMEOUT exceeds typical LB idle timeout."""
        assert KEEP_ALIVE_TIMEOUT > 60

    def test_llm_timeout_reasonable(self) -> None:
        """Verify LLM_TIMEOUT_MS is within a reasonable range."""
        assert LLM_TIMEOUT_MS >= 30_000
        assert LLM_TIMEOUT_MS <= 600_000
