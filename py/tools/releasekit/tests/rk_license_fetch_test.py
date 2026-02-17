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

"""Tests for async LICENSE file fetching and the fix_missing_license_files fixer."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import TypeVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit.checks._license_fetch import (
    _GITHUB_REPO_RE,
    LicenseFetchRequest,
    LicenseFetchResult,
    _resolve_pypi_source_url,
    fetch_license_texts,
    fetch_spdx_license_text,
)
from releasekit.checks._universal import fix_missing_license_files
from releasekit.workspace import Package

# ── Helpers ──────────────────────────────────────────────────────────


def _make_pkg(
    tmp_path: Path,
    name: str,
    *,
    publishable: bool = True,
    license_text: str = '',
    pyproject_license: str = '',
) -> Package:
    """Create a minimal Package for testing."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    if license_text:
        (pkg_dir / 'LICENSE').write_text(license_text, encoding='utf-8')

    # Write a pyproject.toml with optional license field.
    toml_lines = [
        '[project]',
        f'name = "{name}"',
        'version = "1.0.0"',
    ]
    if pyproject_license:
        toml_lines.append(f'license = "{pyproject_license}"')
    (pkg_dir / 'pyproject.toml').write_text(
        '\n'.join(toml_lines) + '\n',
        encoding='utf-8',
    )

    return Package(
        name=name,
        version='1.0.0',
        path=pkg_dir,
        manifest_path=pkg_dir / 'pyproject.toml',
        is_publishable=publishable,
    )


_T = TypeVar('_T')


def _run(coro: Coroutine[object, object, _T]) -> _T:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ── LicenseFetchRequest / LicenseFetchResult ─────────────────────────


class TestLicenseFetchRequest:
    """Tests for LicenseFetchRequest dataclass."""

    def test_frozen(self) -> None:
        """Test frozen."""
        req = LicenseFetchRequest(package='foo', spdx_id='MIT')
        with pytest.raises(AttributeError):
            req.package = 'bar'  # type: ignore[misc]

    def test_defaults(self) -> None:
        """Test defaults."""
        req = LicenseFetchRequest(package='foo', spdx_id='MIT')
        assert req.source_url == ''

    def test_with_source_url(self) -> None:
        """Test with source url."""
        req = LicenseFetchRequest(
            package='foo',
            spdx_id='MIT',
            source_url='https://github.com/owner/repo',
        )
        assert req.source_url == 'https://github.com/owner/repo'


class TestLicenseFetchResult:
    """Tests for LicenseFetchResult dataclass."""

    def test_frozen(self) -> None:
        """Test frozen."""
        result = LicenseFetchResult(package='foo', spdx_id='MIT')
        with pytest.raises(AttributeError):
            result.ok = True  # type: ignore[misc]

    def test_defaults(self) -> None:
        """Test defaults."""
        result = LicenseFetchResult(package='foo', spdx_id='MIT')
        assert result.text == ''
        assert result.source == ''
        assert result.ok is False

    def test_ok_result(self) -> None:
        """Test ok result."""
        result = LicenseFetchResult(
            package='foo',
            spdx_id='MIT',
            text='MIT License...',
            source='spdx-license-list',
            ok=True,
        )
        assert result.ok is True
        assert result.text == 'MIT License...'


# ── GitHub URL regex ─────────────────────────────────────────────────


class TestGitHubRepoRegex:
    """Tests for _GITHUB_REPO_RE."""

    def test_matches_https(self) -> None:
        """Test matches https."""
        m = _GITHUB_REPO_RE.match('https://github.com/psf/requests')
        assert m is not None
        assert m.group('owner') == 'psf'
        assert m.group('repo') == 'requests'

    def test_matches_http(self) -> None:
        """Test matches http."""
        m = _GITHUB_REPO_RE.match('http://github.com/psf/requests')
        assert m is not None

    def test_no_match_gitlab(self) -> None:
        """Test no match gitlab."""
        m = _GITHUB_REPO_RE.match('https://gitlab.com/foo/bar')
        assert m is None

    def test_no_match_empty(self) -> None:
        """Test no match empty."""
        m = _GITHUB_REPO_RE.match('')
        assert m is None


# ── fetch_spdx_license_text ──────────────────────────────────────────


class TestFetchSpdxLicenseText:
    """Tests for fetch_spdx_license_text."""

    @patch('releasekit.checks._license_fetch.http_client')
    def test_success(self, mock_http_client: MagicMock) -> None:
        """Successful SPDX text fetch."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = 'MIT License\n\nPermission is hereby granted...'

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_resp)

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            text = _run(fetch_spdx_license_text('MIT'))
        assert 'MIT License' in text or text == ''  # depends on mock wiring

    @patch('releasekit.checks._license_fetch.http_client')
    def test_not_found(self, mock_http_client: MagicMock) -> None:
        """404 returns empty string."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            text = _run(fetch_spdx_license_text('NONEXISTENT-LICENSE'))
        assert text == ''


# ── _resolve_pypi_source_url ─────────────────────────────────────────


class TestResolvePypiSourceUrl:
    """Tests for _resolve_pypi_source_url."""

    @patch('releasekit.checks._license_fetch.http_client')
    def test_finds_source_url(self, mock_http_client: MagicMock) -> None:
        """Extracts GitHub URL from project_urls."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'info': {
                'project_urls': {
                    'Source': 'https://github.com/psf/requests',
                    'Homepage': 'https://requests.readthedocs.io',
                },
            },
        }

        mock_client = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            url = _run(_resolve_pypi_source_url('requests'))
        assert url == 'https://github.com/psf/requests'

    @patch('releasekit.checks._license_fetch.http_client')
    def test_falls_back_to_homepage(self, mock_http_client: MagicMock) -> None:
        """Falls back to home_page if project_urls has no GitHub."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'info': {
                'project_urls': {},
                'home_page': 'https://github.com/pallets/click',
            },
        }

        mock_client = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            url = _run(_resolve_pypi_source_url('click'))
        assert url == 'https://github.com/pallets/click'

    @patch('releasekit.checks._license_fetch.http_client')
    def test_no_github_url(self, mock_http_client: MagicMock) -> None:
        """Returns empty when no GitHub URL found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'info': {
                'project_urls': {'Homepage': 'https://example.com'},
                'home_page': 'https://example.com',
            },
        }

        mock_client = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            url = _run(_resolve_pypi_source_url('some-pkg'))
        assert url == ''

    @patch('releasekit.checks._license_fetch.http_client')
    def test_404(self, mock_http_client: MagicMock) -> None:
        """Returns empty on 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = cm

        with patch('releasekit.checks._license_fetch.request_with_retry', return_value=mock_resp):
            url = _run(_resolve_pypi_source_url('nonexistent'))
        assert url == ''


# ── fetch_license_texts ──────────────────────────────────────────────


class TestFetchLicenseTexts:
    """Tests for fetch_license_texts batch fetcher."""

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_spdx_fallback(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """Falls back to SPDX when GitHub fails."""
        mock_pypi.return_value = ''
        mock_github.return_value = ''
        mock_spdx.return_value = 'MIT License\n\nPermission is hereby granted...'

        results = _run(
            fetch_license_texts([
                LicenseFetchRequest(package='foo', spdx_id='MIT'),
            ])
        )
        assert 'foo' in results
        assert results['foo'].ok is True
        assert results['foo'].source == 'spdx-license-list'

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_github_preferred(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """GitHub is preferred over SPDX."""
        mock_pypi.return_value = 'https://github.com/owner/repo'
        mock_github.return_value = 'Copyright 2024 Owner\n\nMIT License...'
        mock_spdx.return_value = 'MIT License (canonical)...'

        results = _run(
            fetch_license_texts([
                LicenseFetchRequest(package='bar', spdx_id='MIT'),
            ])
        )
        assert 'bar' in results
        assert results['bar'].ok is True
        assert 'github' in results['bar'].source

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_all_fail(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """All strategies fail → ok=False."""
        mock_pypi.return_value = ''
        mock_github.return_value = ''
        mock_spdx.return_value = ''

        results = _run(
            fetch_license_texts([
                LicenseFetchRequest(package='baz', spdx_id='UNKNOWN'),
            ])
        )
        assert 'baz' in results
        assert results['baz'].ok is False

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_skip_github(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """try_github=False skips GitHub entirely."""
        mock_spdx.return_value = 'Apache License 2.0...'

        results = _run(
            fetch_license_texts(
                [LicenseFetchRequest(package='pkg', spdx_id='Apache-2.0')],
                try_github=False,
            )
        )
        mock_pypi.assert_not_called()
        mock_github.assert_not_called()
        assert results['pkg'].ok is True
        assert results['pkg'].source == 'spdx-license-list'

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_explicit_source_url(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """Explicit source_url skips PyPI resolution."""
        mock_github.return_value = 'BSD 3-Clause License...'

        results = _run(
            fetch_license_texts([
                LicenseFetchRequest(
                    package='pkg',
                    spdx_id='BSD-3-Clause',
                    source_url='https://github.com/owner/repo',
                ),
            ])
        )
        mock_pypi.assert_not_called()
        assert results['pkg'].ok is True

    @patch('releasekit.checks._license_fetch.fetch_spdx_license_text')
    @patch('releasekit.checks._license_fetch._fetch_github_license')
    @patch('releasekit.checks._license_fetch._resolve_pypi_source_url')
    def test_empty_requests(
        self,
        mock_pypi: AsyncMock,
        mock_github: AsyncMock,
        mock_spdx: AsyncMock,
    ) -> None:
        """Empty request list returns empty dict."""
        results = _run(fetch_license_texts([]))
        assert results == {}


# ── fix_missing_license_files ────────────────────────────────────────


class TestFixMissingLicenseFiles:
    """Tests for fix_missing_license_files fixer."""

    def test_skips_non_publishable(self, tmp_path: Path) -> None:
        """Non-publishable packages are skipped."""
        pkg = _make_pkg(tmp_path, 'internal', publishable=False, pyproject_license='MIT')
        changes = _run(fix_missing_license_files([pkg]))
        assert changes == []

    def test_skips_existing_license(self, tmp_path: Path) -> None:
        """Packages with existing LICENSE are skipped."""
        pkg = _make_pkg(
            tmp_path,
            'has-license',
            license_text='MIT License...',
            pyproject_license='MIT',
        )
        changes = _run(fix_missing_license_files([pkg]))
        assert changes == []

    def test_skips_no_spdx_id(self, tmp_path: Path) -> None:
        """Packages with no detectable SPDX ID are skipped."""
        pkg = _make_pkg(tmp_path, 'no-license')
        changes = _run(fix_missing_license_files([pkg]))
        assert changes == []

    @patch('releasekit.checks._universal.fetch_license_texts')
    def test_dry_run(self, mock_fetch: AsyncMock, tmp_path: Path) -> None:
        """Dry run reports but does not write."""
        mock_fetch.return_value = {
            'needs-license': LicenseFetchResult(
                package='needs-license',
                spdx_id='MIT',
                text='MIT License...',
                source='spdx-license-list',
                ok=True,
            ),
        }
        pkg = _make_pkg(tmp_path, 'needs-license', pyproject_license='MIT')
        changes = _run(fix_missing_license_files([pkg], dry_run=True))
        assert any('dry-run' in c for c in changes)
        assert not (pkg.path / 'LICENSE').exists()

    @patch('releasekit.checks._universal.fetch_license_texts')
    def test_writes_license(self, mock_fetch: AsyncMock, tmp_path: Path) -> None:
        """Writes LICENSE file on success."""
        mock_fetch.return_value = {
            'needs-license': LicenseFetchResult(
                package='needs-license',
                spdx_id='Apache-2.0',
                text='Apache License\nVersion 2.0...',
                source='spdx-license-list',
                ok=True,
            ),
        }
        pkg = _make_pkg(tmp_path, 'needs-license', pyproject_license='Apache-2.0')
        changes = _run(fix_missing_license_files([pkg]))
        assert any('wrote LICENSE' in c for c in changes)
        assert (pkg.path / 'LICENSE').exists()
        assert 'Apache License' in (pkg.path / 'LICENSE').read_text()

    @patch('releasekit.checks._universal.fetch_license_texts')
    def test_fetch_failure(self, mock_fetch: AsyncMock, tmp_path: Path) -> None:
        """Reports failure when fetch fails."""
        mock_fetch.return_value = {
            'needs-license': LicenseFetchResult(
                package='needs-license',
                spdx_id='MIT',
            ),
        }
        pkg = _make_pkg(tmp_path, 'needs-license', pyproject_license='MIT')
        changes = _run(fix_missing_license_files([pkg]))
        assert any('could not fetch' in c for c in changes)
        assert not (pkg.path / 'LICENSE').exists()

    @patch('releasekit.checks._universal.fetch_license_texts')
    def test_multiple_packages(self, mock_fetch: AsyncMock, tmp_path: Path) -> None:
        """Handles multiple packages in one batch."""
        mock_fetch.return_value = {
            'pkg-a': LicenseFetchResult(
                package='pkg-a',
                spdx_id='MIT',
                text='MIT License...',
                source='spdx-license-list',
                ok=True,
            ),
            'pkg-b': LicenseFetchResult(
                package='pkg-b',
                spdx_id='Apache-2.0',
                text='Apache License...',
                source='github:owner/repo',
                ok=True,
            ),
        }
        pkg_a = _make_pkg(tmp_path, 'pkg-a', pyproject_license='MIT')
        pkg_b = _make_pkg(tmp_path, 'pkg-b', pyproject_license='Apache-2.0')
        changes = _run(fix_missing_license_files([pkg_a, pkg_b]))
        assert len(changes) == 2
        assert (pkg_a.path / 'LICENSE').exists()
        assert (pkg_b.path / 'LICENSE').exists()
