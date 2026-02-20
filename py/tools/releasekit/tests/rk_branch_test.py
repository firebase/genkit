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

"""Tests for releasekit.branch — default branch resolution."""

from __future__ import annotations

import pytest
from releasekit.branch import resolve_default_branch
from tests._fakes import FakeVCS


class TestResolveDefaultBranch:
    """Tests for resolve_default_branch."""

    @pytest.mark.asyncio
    async def test_config_override_takes_precedence(self) -> None:
        """Config override wins over VCS default."""
        vcs = FakeVCS(default_branch='master')
        result = await resolve_default_branch(vcs, config_override='main')
        assert result == 'main'

    @pytest.mark.asyncio
    async def test_falls_back_to_vcs(self) -> None:
        """Empty override falls back to VCS."""
        vcs = FakeVCS(default_branch='develop')
        result = await resolve_default_branch(vcs, config_override='')
        assert result == 'develop'

    @pytest.mark.asyncio
    async def test_no_override_default_vcs(self) -> None:
        """No override uses VCS default."""
        vcs = FakeVCS(default_branch='main')
        result = await resolve_default_branch(vcs)
        assert result == 'main'

    @pytest.mark.asyncio
    async def test_empty_string_override_uses_vcs(self) -> None:
        """Empty string override falls back to VCS."""
        vcs = FakeVCS(default_branch='trunk')
        result = await resolve_default_branch(vcs, config_override='')
        assert result == 'trunk'
