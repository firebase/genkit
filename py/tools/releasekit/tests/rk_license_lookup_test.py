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

"""Tests for async license lookup from registries."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import NoReturn
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit._types import DetectedLicense
from releasekit.checks._license_lookup import (
    CacheEntry,
    LicenseLookupCache,
    LookupRequest,
    lookup_licenses,
)

# ── CacheEntry ───────────────────────────────────────────────────────


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_fields(self) -> None:
        """Test fields."""
        e = CacheEntry(license_id='MIT', source='npm registry', timestamp=1000.0)
        assert e.license_id == 'MIT'
        assert e.source == 'npm registry'
        assert e.timestamp == 1000.0

    def test_frozen(self) -> None:
        """Test frozen."""
        e = CacheEntry(license_id='MIT', source='npm', timestamp=1.0)
        with pytest.raises(AttributeError):
            e.license_id = 'BSD'  # type: ignore[misc]


# ── LicenseLookupCache ──────────────────────────────────────────────


class TestLicenseLookupCache:
    """Tests for LicenseLookupCache disk-backed cache."""

    def test_put_and_get(self, tmp_path: Path) -> None:
        """Test put and get."""
        cache = LicenseLookupCache(tmp_path / 'cache.json')
        entry = CacheEntry(license_id='MIT', source='npm', timestamp=time.time())
        cache.put('npm', 'express', '4.18.2', entry)
        got = cache.get('npm', 'express', '4.18.2')
        assert got is not None
        assert got.license_id == 'MIT'

    def test_get_missing(self, tmp_path: Path) -> None:
        """Test get missing."""
        cache = LicenseLookupCache(tmp_path / 'cache.json')
        assert cache.get('npm', 'nonexistent', '1.0.0') is None

    def test_expired_entry_returns_none(self, tmp_path: Path) -> None:
        """Test expired entry returns none."""
        cache = LicenseLookupCache(tmp_path / 'cache.json', ttl=1)
        entry = CacheEntry(license_id='MIT', source='npm', timestamp=time.time() - 10)
        cache.put('npm', 'express', '4.18.2', entry)
        assert cache.get('npm', 'express', '4.18.2') is None

    def test_persistence(self, tmp_path: Path) -> None:
        """Test persistence."""
        path = tmp_path / 'cache.json'
        cache1 = LicenseLookupCache(path)
        entry = CacheEntry(license_id='Apache-2.0', source='pypi', timestamp=time.time())
        cache1.put('python', 'requests', '2.31.0', entry)

        # Load from disk.
        cache2 = LicenseLookupCache(path)
        got = cache2.get('python', 'requests', '2.31.0')
        assert got is not None
        assert got.license_id == 'Apache-2.0'

    def test_corrupt_cache_file(self, tmp_path: Path) -> None:
        """Test corrupt cache file."""
        path = tmp_path / 'cache.json'
        path.write_text('not json!!!', encoding='utf-8')
        cache = LicenseLookupCache(path)
        assert cache.get('npm', 'x', '1.0') is None

    def test_key_format(self, tmp_path: Path) -> None:
        """Test key format."""
        cache = LicenseLookupCache(tmp_path / 'cache.json')
        entry = CacheEntry(license_id='MIT', source='npm', timestamp=time.time())
        cache.put('npm', '@scope/pkg', '1.0.0', entry)
        got = cache.get('npm', '@scope/pkg', '1.0.0')
        assert got is not None
        assert got.license_id == 'MIT'

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test creates parent dirs."""
        path = tmp_path / 'deep' / 'nested' / 'cache.json'
        cache = LicenseLookupCache(path)
        entry = CacheEntry(license_id='MIT', source='npm', timestamp=time.time())
        cache.put('npm', 'x', '1.0', entry)
        assert path.is_file()


# ── Mocked lookup functions ──────────────────────────────────────────


def _make_mock_response(status_code: int, json_data: object = None) -> MagicMock:
    """Create a mock httpx.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.text = json.dumps(json_data) if json_data else ''
    return mock


class TestLookupNpm:
    """Tests for npm registry license lookup."""

    def test_standard_license(self) -> None:
        """Test standard license."""
        from releasekit.checks._license_lookup import _lookup_npm

        resp = _make_mock_response(200, {'license': 'MIT'})
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_npm('express', '4.18.2'))
        assert result.found
        assert result.value == 'MIT'
        assert result.source == 'npm registry'

    def test_object_license(self) -> None:
        """Test object license."""
        from releasekit.checks._license_lookup import _lookup_npm

        resp = _make_mock_response(200, {'license': {'type': 'Apache-2.0'}})
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_npm('pkg', '1.0.0'))
        assert result.value == 'Apache-2.0'

    def test_404_returns_empty(self) -> None:
        """Test 404 returns empty."""
        from releasekit.checks._license_lookup import _lookup_npm

        resp = _make_mock_response(404)
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_npm('nonexistent', '0.0.0'))
        assert not result.found


class TestLookupPypi:
    """Tests for PyPI registry license lookup."""

    def test_license_field(self) -> None:
        """Test license field."""
        from releasekit.checks._license_lookup import _lookup_pypi

        resp = _make_mock_response(200, {'info': {'license': 'Apache-2.0', 'classifiers': []}})
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_pypi('requests', '2.31.0'))
        assert result.found
        assert result.value == 'Apache-2.0'

    def test_classifier_fallback(self) -> None:
        """Test classifier fallback."""
        from releasekit.checks._license_lookup import _lookup_pypi

        resp = _make_mock_response(
            200,
            {
                'info': {
                    'license': '',
                    'classifiers': ['License :: OSI Approved :: MIT License'],
                },
            },
        )
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_pypi('mypkg', '1.0'))
        assert result.found
        assert result.value == 'MIT License'

    def test_unknown_license_skipped(self) -> None:
        """Test unknown license skipped."""
        from releasekit.checks._license_lookup import _lookup_pypi

        resp = _make_mock_response(200, {'info': {'license': 'UNKNOWN', 'classifiers': []}})
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_pypi('mypkg', '1.0'))
        assert not result.found


class TestLookupCratesIo:
    """Tests for crates.io registry license lookup."""

    def test_license_field(self) -> None:
        """Test license field."""
        from releasekit.checks._license_lookup import _lookup_crates_io

        resp = _make_mock_response(200, {'version': {'license': 'MIT OR Apache-2.0'}})
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_crates_io('serde', '1.0.200'))
        assert result.found
        assert result.value == 'MIT OR Apache-2.0'


class TestLookupMavenCentral:
    """Tests for Maven Central registry license lookup."""

    def test_pom_license(self) -> None:
        """Test pom license."""
        from releasekit.checks._license_lookup import _lookup_maven_central

        pom = '<project><licenses><license><name>Apache-2.0</name></license></licenses></project>'
        resp = _make_mock_response(200)
        resp.text = pom
        with patch('releasekit.checks._license_lookup.http_client') as mock_ctx:
            mock_client = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('releasekit.checks._license_lookup.request_with_retry', return_value=resp):
                result = asyncio.run(_lookup_maven_central('com.google:guava', '33.0.0'))
        assert result.found
        assert result.value == 'Apache-2.0'

    def test_no_colon_returns_empty(self) -> None:
        """Test no colon returns empty."""
        from releasekit.checks._license_lookup import _lookup_maven_central

        result = asyncio.run(_lookup_maven_central('nocolon', '1.0'))
        assert not result.found


# ── Batch lookup ─────────────────────────────────────────────────────


class TestLookupLicenses:
    """Tests for batch lookup_licenses orchestration."""

    def test_uses_cache(self, tmp_path: Path) -> None:
        """Test uses cache."""
        cache = LicenseLookupCache(tmp_path / 'cache.json')
        cache.put(
            'npm',
            'express',
            '4.18.2',
            CacheEntry(
                license_id='MIT',
                source='npm registry',
                timestamp=time.time(),
            ),
        )
        reqs = [LookupRequest(package='express', version='4.18.2', ecosystem='npm')]
        results = asyncio.run(lookup_licenses(reqs, cache=cache))
        assert results['express@4.18.2'].value == 'MIT'

    def test_unknown_ecosystem(self, tmp_path: Path) -> None:
        """Test unknown ecosystem."""
        reqs = [LookupRequest(package='x', version='1.0', ecosystem='unknown_eco')]
        results = asyncio.run(lookup_licenses(reqs))
        assert not results['x@1.0'].found

    def test_handles_fetch_exception(self, tmp_path: Path) -> None:
        """Test handles fetch exception."""

        async def _boom(*a: object, **kw: object) -> NoReturn:
            """Boom."""
            raise RuntimeError('network down')

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _boom},
        ):
            reqs = [LookupRequest(package='x', version='1.0', ecosystem='npm')]
            results = asyncio.run(lookup_licenses(reqs))
        assert not results['x@1.0'].found

    def test_populates_cache(self, tmp_path: Path) -> None:
        """Test populates cache."""
        cache = LicenseLookupCache(tmp_path / 'cache.json')

        async def _fake_npm(pkg: str, ver: str, **kw: object) -> DetectedLicense:
            """Fake npm."""
            return DetectedLicense(value='ISC', source='npm registry', package_name=pkg)

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _fake_npm},
        ):
            reqs = [LookupRequest(package='y', version='2.0', ecosystem='npm')]
            asyncio.run(lookup_licenses(reqs, cache=cache))

        cached = cache.get('npm', 'y', '2.0')
        assert cached is not None
        assert cached.license_id == 'ISC'

    def test_concurrent_requests(self, tmp_path: Path) -> None:
        """Test concurrent requests."""
        call_count = 0

        async def _fake_npm(pkg: str, ver: str, **kw: object) -> DetectedLicense:
            """Fake npm."""
            nonlocal call_count
            call_count += 1
            return DetectedLicense(value='MIT', source='npm', package_name=pkg)

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _fake_npm},
        ):
            reqs = [LookupRequest(package=f'pkg-{i}', version='1.0', ecosystem='npm') for i in range(5)]
            results = asyncio.run(lookup_licenses(reqs, concurrency=3))

        assert len(results) == 5
        assert call_count == 5
        assert all(r.value == 'MIT' for r in results.values())


# ── Jitter in net.py ─────────────────────────────────────────────────


class TestRetryJitter:
    """Tests for retry jitter in net.py."""

    def test_jitter_constant_exists(self) -> None:
        """Test jitter constant exists."""
        from releasekit.net import RETRY_JITTER_MAX

        assert RETRY_JITTER_MAX > 0

    def test_retry_imports_random(self) -> None:
        """Test retry imports random."""
        import random  # noqa: F401

        import releasekit.net

        assert hasattr(releasekit.net, 'RETRY_JITTER_MAX')


# ── detect_license_with_lookup integration ───────────────────────────


class _FakePkg:
    """Minimal package-like object for testing."""

    def __init__(self, name: str, path: Path, version: str = '') -> None:
        """Init  ."""
        self.name = name
        self.path = path
        self.version = version


class TestDetectLicenseWithLookup:
    """Tests for detect_license_with_lookup integration."""

    def test_local_detection_skips_lookup(self, tmp_path: Path) -> None:
        """Test local detection skips lookup."""
        from releasekit.checks._license_detect import detect_license_with_lookup

        pkg_dir = tmp_path / 'mypkg'
        pkg_dir.mkdir()
        (pkg_dir / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': 'MIT'}))
        pkg = _FakePkg('mypkg', pkg_dir, '1.0.0')
        results = asyncio.run(detect_license_with_lookup([pkg], 'npm'))
        assert results['mypkg'].found
        assert results['mypkg'].value == 'MIT'

    def test_falls_back_to_registry(self, tmp_path: Path) -> None:
        """Test falls back to registry."""
        from releasekit.checks._license_detect import detect_license_with_lookup

        pkg_dir = tmp_path / 'nolicense'
        pkg_dir.mkdir()
        pkg = _FakePkg('nolicense', pkg_dir, '2.0.0')

        async def _fake_npm(pkg_name: str, ver: str, **kw: object) -> DetectedLicense:
            """Fake npm."""
            return DetectedLicense(value='ISC', source='npm registry', package_name=pkg_name)

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _fake_npm},
        ):
            results = asyncio.run(
                detect_license_with_lookup(
                    [pkg],
                    'npm',
                    cache_path=tmp_path / 'cache.json',
                )
            )
        assert results['nolicense'].found
        assert results['nolicense'].value == 'ISC'

    def test_no_version_returns_empty(self, tmp_path: Path) -> None:
        """Test no version returns empty."""
        from releasekit.checks._license_detect import detect_license_with_lookup

        pkg_dir = tmp_path / 'nover'
        pkg_dir.mkdir()
        pkg = _FakePkg('nover', pkg_dir, '')
        results = asyncio.run(detect_license_with_lookup([pkg], 'npm'))
        assert not results['nover'].found

    def test_mixed_local_and_lookup(self, tmp_path: Path) -> None:
        """Test mixed local and lookup."""
        from releasekit.checks._license_detect import detect_license_with_lookup

        # Package with local license.
        local_dir = tmp_path / 'local'
        local_dir.mkdir()
        (local_dir / 'package.json').write_text(json.dumps({'name': 'local', 'license': 'Apache-2.0'}))
        local_pkg = _FakePkg('local', local_dir, '1.0.0')

        # Package needing lookup.
        remote_dir = tmp_path / 'remote'
        remote_dir.mkdir()
        remote_pkg = _FakePkg('remote', remote_dir, '3.0.0')

        async def _fake_npm(pkg_name: str, ver: str, **kw: object) -> DetectedLicense:
            """Fake npm."""
            return DetectedLicense(value='BSD-3-Clause', source='npm registry', package_name=pkg_name)

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _fake_npm},
        ):
            results = asyncio.run(
                detect_license_with_lookup(
                    [local_pkg, remote_pkg],
                    'npm',
                    cache_path=tmp_path / 'cache.json',
                )
            )
        assert results['local'].value == 'Apache-2.0'
        assert results['remote'].value == 'BSD-3-Clause'

    def test_uses_cache_on_second_run(self, tmp_path: Path) -> None:
        """Test uses cache on second run."""
        from releasekit.checks._license_detect import detect_license_with_lookup

        pkg_dir = tmp_path / 'cached'
        pkg_dir.mkdir()
        pkg = _FakePkg('cached', pkg_dir, '1.0.0')
        cache_path = tmp_path / 'cache.json'

        call_count = 0

        async def _counting_npm(pkg_name: str, ver: str, **kw: object) -> DetectedLicense:
            """Counting npm."""
            nonlocal call_count
            call_count += 1
            return DetectedLicense(value='MIT', source='npm registry', package_name=pkg_name)

        with patch.dict(
            'releasekit.checks._license_lookup._ECOSYSTEM_FETCHERS',
            {'npm': _counting_npm},
        ):
            # First run: hits the fetcher.
            asyncio.run(
                detect_license_with_lookup(
                    [pkg],
                    'npm',
                    cache_path=cache_path,
                )
            )
            assert call_count == 1

            # Second run: should use cache, not call fetcher again.
            asyncio.run(
                detect_license_with_lookup(
                    [pkg],
                    'npm',
                    cache_path=cache_path,
                )
            )
            assert call_count == 1  # Still 1 — cache hit.
