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

"""Tests for releasekit.prepare module."""

from __future__ import annotations

from releasekit.prepare import PrepareResult, _build_pr_body, _embed_manifest, _package_paths
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

# ── Tests: PrepareResult ──


class TestPrepareResult:
    """Tests for PrepareResult dataclass."""

    def test_empty_is_ok(self) -> None:
        """Empty result is OK with no bumps or skips."""
        result = PrepareResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.bumped:
            raise AssertionError('Expected no bumped')
        if result.skipped:
            raise AssertionError('Expected no skipped')

    def test_with_errors(self) -> None:
        """Result with errors is not OK."""
        result = PrepareResult(errors={'preflight:dirty': 'unclean'})
        if result.ok:
            raise AssertionError('Should not be OK with errors')

    def test_with_bumped(self) -> None:
        """Result with bumped packages is OK."""
        ver = PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')
        result = PrepareResult(bumped=[ver])
        if not result.ok:
            raise AssertionError('Bumped result should be OK')
        if len(result.bumped) != 1:
            raise AssertionError(f'Expected 1 bumped, got {len(result.bumped)}')


# ── Tests: _embed_manifest ──


class TestEmbedManifest:
    """Tests for _embed_manifest."""

    def test_appends_when_no_markers(self) -> None:
        """Appends manifest block when no markers exist."""
        body = '# Release\nSome content.'
        result = _embed_manifest(body, '{"test": true}')
        if '<!-- releasekit:manifest:start -->' not in result:
            raise AssertionError('Missing start marker')
        if '<!-- releasekit:manifest:end -->' not in result:
            raise AssertionError('Missing end marker')
        if '{"test": true}' not in result:
            raise AssertionError('Missing JSON content')

    def test_replaces_existing_markers(self) -> None:
        """Replaces existing manifest block in-place."""
        body = (
            '# Release\n'
            '<!-- releasekit:manifest:start -->\n'
            '```json\n{"old": true}\n```\n'
            '<!-- releasekit:manifest:end -->\n'
        )
        result = _embed_manifest(body, '{"new": true}')
        if '{"old": true}' in result:
            raise AssertionError('Old manifest should be replaced')
        if '{"new": true}' not in result:
            raise AssertionError('New manifest should be present')
        if '<!-- releasekit:manifest:start -->' not in result:
            raise AssertionError('Start marker should be present')
        if '<!-- releasekit:manifest:end -->' not in result:
            raise AssertionError('End marker should be present')

    def test_json_in_code_block(self) -> None:
        """Manifest is wrapped in a JSON code block."""
        result = _embed_manifest('body', '{}')
        if '```json' not in result:
            raise AssertionError('JSON should be in a code block')


# ── Tests: _build_pr_body ──


class TestBuildPrBody:
    """Tests for _build_pr_body."""

    def test_includes_version_header(self) -> None:
        """PR body includes release version header."""
        body = _build_pr_body({'genkit': '## genkit v0.2.0\n- feat: new'}, '{}', '0.2.0')
        if '# Release v0.2.0' not in body:
            raise AssertionError('Missing version header')

    def test_includes_changelogs(self) -> None:
        """PR body includes changelogs for all packages."""
        changelogs = {
            'a': '## a\n- fix',
            'b': '## b\n- feat',
        }
        body = _build_pr_body(changelogs, '{}', '1.0.0')
        if '## a' not in body:
            raise AssertionError('Missing changelog for a')
        if '## b' not in body:
            raise AssertionError('Missing changelog for b')

    def test_embeds_manifest(self) -> None:
        """PR body contains embedded release manifest."""
        body = _build_pr_body({}, '{"x":1}', '1.0.0')
        if '<!-- releasekit:manifest:start -->' not in body:
            raise AssertionError('Missing manifest')


# ── Tests: _package_paths ──


class TestPackagePaths:
    """Tests for _package_paths."""

    def test_builds_name_to_path_map(self, tmp_path: object) -> None:
        """Maps package names to their directory paths."""
        from pathlib import Path

        pkg_path = Path('/workspace/packages/genkit')
        pkg = Package(
            name='genkit',
            version='0.1.0',
            path=pkg_path,
            pyproject_path=pkg_path / 'pyproject.toml',
        )
        paths = _package_paths([pkg])
        if paths.get('genkit') != str(pkg_path):
            raise AssertionError(f'Unexpected path: {paths}')

    def test_empty_packages(self) -> None:
        """Empty input returns empty map."""
        if _package_paths([]):
            raise AssertionError('Expected empty map')
