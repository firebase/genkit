# Copyright 2025 Google LLC
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

"""Tests for releasekit.backends.forge module."""

from __future__ import annotations

from pathlib import Path

from releasekit.backends.forge import Forge, GitHubBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestGitHubBackendProtocol:
    """Verify GitHubBackend implements the Forge protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """GitHubBackend should be a runtime-checkable Forge."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        assert isinstance(backend, Forge)


class TestGitHubBackendDryRun:
    """Tests for GitHubBackend in dry-run mode."""

    def test_create_release_dry_run(self, tmp_path: Path) -> None:
        """create_release() in dry-run should return synthetic success."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.create_release('v1.0.0', title='Release v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    def test_create_release_draft(self, tmp_path: Path) -> None:
        """create_release(draft=True) should include --draft."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.create_release('v1.0.0', draft=True, dry_run=True)
        assert '--draft' in result.command

    def test_create_release_prerelease(self, tmp_path: Path) -> None:
        """create_release(prerelease=True) should include --prerelease."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.create_release('v1.0.0', prerelease=True, dry_run=True)
        assert '--prerelease' in result.command

    def test_delete_release_dry_run(self, tmp_path: Path) -> None:
        """delete_release() in dry-run should return synthetic success."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.delete_release('v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    def test_promote_release_dry_run(self, tmp_path: Path) -> None:
        """promote_release() in dry-run should return synthetic success."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.promote_release('v1.0.0', dry_run=True)
        assert result.ok

    def test_create_pr_dry_run(self, tmp_path: Path) -> None:
        """create_pr() in dry-run should include branch info."""
        backend = GitHubBackend(repo='firebase/genkit', cwd=tmp_path)
        result = backend.create_pr(
            title='Test PR',
            head='feat/test',
            body='Test body',
            dry_run=True,
        )
        assert result.ok
        assert 'feat/test' in result.command
