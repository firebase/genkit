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

"""Tests for releasekit.backends.registry module."""

from __future__ import annotations

import pytest
from releasekit.backends.registry import PyPIBackend, Registry
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestPyPIBackendProtocol:
    """Verify PyPIBackend implements the Registry protocol."""

    def test_implements_protocol(self) -> None:
        """PyPIBackend should be a runtime-checkable Registry."""
        backend = PyPIBackend()
        assert isinstance(backend, Registry)


class TestPyPIBackendCheckPublished:
    """Tests for PyPIBackend.check_published()."""

    @pytest.mark.asyncio
    async def test_known_package(self) -> None:
        """Should return True for a known published package."""
        backend = PyPIBackend()
        result = await backend.check_published('pip', '24.0')
        assert result is True

    @pytest.mark.asyncio
    async def test_unknown_version(self) -> None:
        """Should return False for a non-existent version."""
        backend = PyPIBackend()
        result = await backend.check_published('pip', '999.999.999')
        assert result is False


class TestPyPIBackendProjectExists:
    """Tests for PyPIBackend.project_exists()."""

    @pytest.mark.asyncio
    async def test_known_project(self) -> None:
        """Should return True for a known project."""
        backend = PyPIBackend()
        result = await backend.project_exists('pip')
        assert result is True

    @pytest.mark.asyncio
    async def test_unknown_project(self) -> None:
        """Should return False for a non-existent project."""
        backend = PyPIBackend()
        result = await backend.project_exists('this-package-definitely-does-not-exist-12345678')
        assert result is False


class TestPyPIBackendLatestVersion:
    """Tests for PyPIBackend.latest_version()."""

    @pytest.mark.asyncio
    async def test_known_package(self) -> None:
        """Should return a version string for a known package."""
        backend = PyPIBackend()
        version = await backend.latest_version('pip')
        assert version is not None
        assert '.' in version

    @pytest.mark.asyncio
    async def test_unknown_package(self) -> None:
        """Should return None for a non-existent package."""
        backend = PyPIBackend()
        version = await backend.latest_version('this-package-definitely-does-not-exist-12345678')
        assert version is None
