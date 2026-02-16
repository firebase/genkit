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

"""Tests for releasekit.api — programmatic Python API."""

from __future__ import annotations

from pathlib import Path

from releasekit.api import ReleaseKit, ReleaseResult
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# ReleaseResult
# ---------------------------------------------------------------------------


class TestReleaseResult:
    """Tests for ReleaseResult dataclass."""

    def test_ok_by_default(self) -> None:
        """Result is ok by default."""
        result = ReleaseResult()
        assert result.ok is True

    def test_summary_no_versions(self) -> None:
        """Summary with no versions."""
        result = ReleaseResult()
        assert '0 packages' in result.summary()

    def test_summary_with_errors(self) -> None:
        """Summary with errors."""
        result = ReleaseResult(ok=False, errors={'plan': 'failed'})
        assert 'Failed' in result.summary()
        assert '1 errors' in result.summary()


# ---------------------------------------------------------------------------
# ReleaseKit
# ---------------------------------------------------------------------------


class TestReleaseKit:
    """Tests for ReleaseKit class."""

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        """Can initialize with a string path."""
        rk = ReleaseKit(str(tmp_path))
        assert rk._root == tmp_path.resolve()

    def test_init_with_path_object(self, tmp_path: Path) -> None:
        """Can initialize with a Path object."""
        rk = ReleaseKit(tmp_path)
        assert rk._root == tmp_path.resolve()

    def test_workspace_label_stored(self, tmp_path: Path) -> None:
        """Workspace label is stored."""
        rk = ReleaseKit(tmp_path, workspace_label='py')
        assert rk._label == 'py'

    def test_config_lazy_loaded(self, tmp_path: Path) -> None:
        """Config is not loaded until accessed."""
        rk = ReleaseKit(tmp_path)
        assert rk._config is None

    def test_ws_config_lazy_loaded(self, tmp_path: Path) -> None:
        """Workspace config is not loaded until accessed."""
        rk = ReleaseKit(tmp_path)
        assert rk._ws_config is None
