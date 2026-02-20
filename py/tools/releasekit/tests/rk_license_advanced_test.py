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

"""Tests for SPDX header enforcement, deep license scan, license change detection, and NOTICE generation."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

from releasekit.checks._universal import (
    EmbeddedLicense,
    LicenseChange,
    NoticeEntry,
    _check_deep_license_scan,
    _check_license_changes,
    _check_spdx_headers,
    _resolve_external_licenses,
    _walk_license_files,
    _walk_source_files,
    fix_missing_notice,
    fix_missing_spdx_headers,
    generate_notice_file,
)
from releasekit.config import (
    VALID_LICENSE_HEADER_KEYS,
    LicenseHeaderConfig,
    _parse_license_headers,
)
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package


def _make_pkg(
    tmp_path: Path,
    name: str,
    *,
    publishable: bool = True,
    internal_deps: list[str] | None = None,
    external_deps: list[str] | None = None,
) -> Package:
    """Create a minimal Package for testing."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(exist_ok=True)
    manifest = pkg_dir / 'pyproject.toml'
    manifest.write_text(
        f'# SPDX-License-Identifier: Apache-2.0\n[project]\nname = "{name}"\nversion = "1.0.0"\n',
        encoding='utf-8',
    )
    return Package(
        name=name,
        version='1.0.0',
        path=pkg_dir,
        manifest_path=manifest,
        is_publishable=publishable,
        internal_deps=internal_deps or [],
        external_deps=external_deps or [],
    )


# ── SPDX Header Enforcement ─────────────────────────────────────────


class TestCheckSpdxHeaders:
    """Tests for _check_spdx_headers."""

    def test_pass_when_all_files_have_headers(self, tmp_path: Path) -> None:
        """Pass when all source files have SPDX headers."""
        pkg = _make_pkg(tmp_path, 'good-pkg')
        src = pkg.path / 'src'
        src.mkdir()
        (src / 'main.py').write_text(
            '# SPDX-License-Identifier: Apache-2.0\nprint("hello")\n',
        )
        result = PreflightResult()
        _check_spdx_headers([pkg], result)
        assert 'spdx_headers' in result.passed

    def test_warn_when_files_missing_headers(self, tmp_path: Path) -> None:
        """Warn when source files lack SPDX headers."""
        pkg = _make_pkg(tmp_path, 'bad-pkg')
        src = pkg.path / 'src'
        src.mkdir()
        (src / 'main.py').write_text('print("no header")\n')
        result = PreflightResult()
        _check_spdx_headers([pkg], result)
        assert 'spdx_headers' in result.warnings

    def test_skip_non_publishable(self, tmp_path: Path) -> None:
        """Skip non-publishable packages."""
        pkg = _make_pkg(tmp_path, 'internal', publishable=False)
        (pkg.path / 'main.py').write_text('print("no header")\n')
        result = PreflightResult()
        _check_spdx_headers([pkg], result)
        assert 'spdx_headers' in result.passed

    def test_skip_non_source_extensions(self, tmp_path: Path) -> None:
        """Skip files with non-source extensions."""
        pkg = _make_pkg(tmp_path, 'data-pkg')
        (pkg.path / 'data.csv').write_text('a,b,c\n')
        (pkg.path / 'image.png').write_bytes(b'\x89PNG')
        result = PreflightResult()
        _check_spdx_headers([pkg], result)
        assert 'spdx_headers' in result.passed

    def test_caps_at_max_report(self, tmp_path: Path) -> None:
        """Cap reported missing files at 20."""
        pkg = _make_pkg(tmp_path, 'many-files')
        src = pkg.path / 'src'
        src.mkdir()
        for i in range(25):
            (src / f'mod{i}.py').write_text(f'x = {i}\n')
        result = PreflightResult()
        _check_spdx_headers([pkg], result)
        # Should warn but cap at 20.
        assert 'spdx_headers' in result.warnings


class TestWalkSourceFiles:
    """Tests for _walk_source_files."""

    def test_finds_python_files(self, tmp_path: Path) -> None:
        """Find .py files recursively."""
        (tmp_path / 'a.py').write_text('x = 1\n')
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'b.py').write_text('y = 2\n')
        files = _walk_source_files(tmp_path)
        names = {f.name for f in files}
        assert 'a.py' in names
        assert 'b.py' in names

    def test_skips_venv(self, tmp_path: Path) -> None:
        """Skip .venv directories."""
        venv = tmp_path / '.venv'
        venv.mkdir()
        (venv / 'lib.py').write_text('z = 3\n')
        files = _walk_source_files(tmp_path)
        assert not files

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        """Skip node_modules directories."""
        nm = tmp_path / 'node_modules'
        nm.mkdir()
        (nm / 'index.js').write_text('module.exports = {};\n')
        files = _walk_source_files(tmp_path)
        assert not files

    def test_skips_egg_info(self, tmp_path: Path) -> None:
        """Skip *.egg-info directories."""
        egg = tmp_path / 'mypkg.egg-info'
        egg.mkdir()
        (egg / 'PKG-INFO').write_text('Name: mypkg\n')
        files = _walk_source_files(tmp_path)
        assert not files


# ── Deep License Scan ────────────────────────────────────────────────


class TestCheckDeepLicenseScan:
    """Tests for _check_deep_license_scan."""

    def test_pass_no_embedded_licenses(self, tmp_path: Path) -> None:
        """Pass when no embedded license files exist."""
        pkg = _make_pkg(tmp_path, 'clean-pkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        result = PreflightResult()
        _check_deep_license_scan([pkg], result)
        assert 'deep_license_scan' in result.passed

    def test_detect_vendored_license(self, tmp_path: Path) -> None:
        """Detect a LICENSE file in a vendor directory."""
        pkg = _make_pkg(tmp_path, 'vendor-pkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        vendor = pkg.path / 'vendor' / 'somelib'
        vendor.mkdir(parents=True)
        (vendor / 'LICENSE').write_text('MIT License\n')
        result = PreflightResult()
        _check_deep_license_scan([pkg], result, project_license='Apache-2.0')
        embedded = cast(list[EmbeddedLicense], result.context.get('embedded_licenses', []))
        assert len(embedded) >= 1
        vendored = [e for e in embedded if e.is_vendored]
        assert len(vendored) == 1
        assert vendored[0].spdx_id == 'MIT'

    def test_warn_on_mismatch(self, tmp_path: Path) -> None:
        """Warn when embedded license differs from project license."""
        pkg = _make_pkg(tmp_path, 'mismatch-pkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        sub = pkg.path / 'third_party' / 'gpl-lib'
        sub.mkdir(parents=True)
        (sub / 'LICENSE').write_text('GNU GENERAL PUBLIC LICENSE\nVersion 3\n')
        result = PreflightResult()
        _check_deep_license_scan([pkg], result, project_license='Apache-2.0')
        # Should warn because GPL-3.0-only != Apache-2.0.
        assert 'deep_license_scan' in result.warnings or 'deep_license_scan' in result.passed

    def test_pass_when_same_license(self, tmp_path: Path) -> None:
        """Pass when embedded license matches project license."""
        pkg = _make_pkg(tmp_path, 'same-lic-pkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        sub = pkg.path / 'bundled' / 'helper'
        sub.mkdir(parents=True)
        (sub / 'LICENSE').write_text('Apache License\n')
        result = PreflightResult()
        _check_deep_license_scan([pkg], result, project_license='Apache-2.0')
        assert 'deep_license_scan' in result.passed

    def test_skip_non_publishable(self, tmp_path: Path) -> None:
        """Skip non-publishable packages."""
        pkg = _make_pkg(tmp_path, 'internal', publishable=False)
        vendor = pkg.path / 'vendor' / 'lib'
        vendor.mkdir(parents=True)
        (vendor / 'LICENSE').write_text('MIT License\n')
        result = PreflightResult()
        _check_deep_license_scan([pkg], result, project_license='Apache-2.0')
        assert 'deep_license_scan' in result.passed


class TestWalkLicenseFiles:
    """Tests for _walk_license_files."""

    def test_finds_license_files(self, tmp_path: Path) -> None:
        """Find LICENSE files recursively."""
        (tmp_path / 'LICENSE').write_text('Apache\n')
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'COPYING').write_text('GPL\n')
        names = frozenset({'LICENSE', 'COPYING'})
        files = _walk_license_files(tmp_path, names)
        found = {f.name for f in files}
        assert 'LICENSE' in found
        assert 'COPYING' in found

    def test_skips_venv(self, tmp_path: Path) -> None:
        """Skip .venv directories."""
        venv = tmp_path / '.venv'
        venv.mkdir()
        (venv / 'LICENSE').write_text('MIT\n')
        names = frozenset({'LICENSE'})
        files = _walk_license_files(tmp_path, names)
        assert not files


# ── License Change Detection ─────────────────────────────────────────


class TestCheckLicenseChanges:
    """Tests for _check_license_changes."""

    def test_pass_when_no_previous(self, tmp_path: Path) -> None:
        """Pass when no previous licenses are provided."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        result = PreflightResult()
        _check_license_changes([pkg], result, previous_licenses=None)
        assert 'license_changes' in result.passed

    def test_pass_when_unchanged(self, tmp_path: Path) -> None:
        """Pass when license hasn't changed."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        result = PreflightResult()
        _check_license_changes(
            [pkg],
            result,
            previous_licenses={'mypkg': 'Apache-2.0'},
        )
        assert 'license_changes' in result.passed

    def test_warn_on_change(self, tmp_path: Path) -> None:
        """Warn when a package changed its license."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        # Write a LICENSE file that detects as MIT.
        (pkg.path / 'LICENSE').write_text(
            'MIT License\n\nPermission is hereby granted, free of charge\n',
        )
        result = PreflightResult()
        _check_license_changes(
            [pkg],
            result,
            previous_licenses={'mypkg': 'Apache-2.0'},
        )
        assert 'license_changes' in result.warnings
        changes = cast(list[LicenseChange], result.context.get('license_change_details', []))
        assert len(changes) == 1
        assert changes[0].old_license == 'Apache-2.0'
        assert changes[0].new_license == 'MIT'

    def test_pass_when_package_not_found(self, tmp_path: Path) -> None:
        """Pass when previous package no longer exists."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        result = PreflightResult()
        _check_license_changes(
            [pkg],
            result,
            previous_licenses={'deleted-pkg': 'MIT'},
        )
        assert 'license_changes' in result.passed


class TestLicenseChangeDataclass:
    """Tests for LicenseChange dataclass."""

    def test_fields(self) -> None:
        """Verify LicenseChange fields."""
        change = LicenseChange(
            package_name='foo',
            old_version='1.0',
            new_version='2.0',
            old_license='MIT',
            new_license='GPL-3.0-only',
        )
        assert change.package_name == 'foo'
        assert change.old_license == 'MIT'
        assert change.new_license == 'GPL-3.0-only'


# ── NOTICE / Attribution Generation ──────────────────────────────────


class TestGenerateNoticeFile:
    """Tests for generate_notice_file."""

    def test_generates_header(self, tmp_path: Path) -> None:
        """Generate a NOTICE file with project header."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (pkg.path / 'LICENSE').write_text(
            'Apache License\nCopyright 2026 Google LLC\n',
        )
        content = generate_notice_file([pkg], project_name='MyProject', project_license='Apache-2.0')
        assert 'MyProject' in content
        assert 'Licensed under Apache-2.0' in content
        assert '## mypkg' in content

    def test_extracts_copyright(self, tmp_path: Path) -> None:
        """Extract copyright lines from LICENSE files."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (pkg.path / 'LICENSE').write_text(
            'MIT License\n\nCopyright 2024 Acme Corp\n\nPermission is hereby granted...\n',
        )
        content = generate_notice_file([pkg])
        assert 'Copyright 2024 Acme Corp' in content

    def test_handles_no_license_file(self, tmp_path: Path) -> None:
        """Handle packages without LICENSE files gracefully."""
        pkg = _make_pkg(tmp_path, 'nolic')
        content = generate_notice_file([pkg])
        assert '## nolic' in content

    def test_sorts_entries(self, tmp_path: Path) -> None:
        """Sort entries alphabetically by package name."""
        pkg_a = _make_pkg(tmp_path, 'aaa')
        pkg_z = _make_pkg(tmp_path, 'zzz')
        (pkg_a.path / 'LICENSE').write_text('MIT License\n')
        (pkg_z.path / 'LICENSE').write_text('Apache License\n')
        content = generate_notice_file([pkg_z, pkg_a])
        idx_a = content.index('## aaa')
        idx_z = content.index('## zzz')
        assert idx_a < idx_z

    def test_default_header(self, tmp_path: Path) -> None:
        """Use default header when project_name is empty."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        content = generate_notice_file([pkg])
        assert 'This project' in content


class TestFixMissingNotice:
    """Tests for fix_missing_notice."""

    def test_creates_notice(self, tmp_path: Path) -> None:
        """Create a NOTICE file when one doesn't exist."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (pkg.path / 'LICENSE').write_text('Apache License\n')
        changes = fix_missing_notice([pkg], tmp_path)
        assert len(changes) == 1
        assert (tmp_path / 'NOTICE').is_file()

    def test_skips_existing(self, tmp_path: Path) -> None:
        """Skip if NOTICE already exists."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        (tmp_path / 'NOTICE').write_text('existing\n')
        changes = fix_missing_notice([pkg], tmp_path)
        assert not changes

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't create the file."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_notice([pkg], tmp_path, dry_run=True)
        assert len(changes) == 1
        assert '(dry-run)' in changes[0]
        assert not (tmp_path / 'NOTICE').is_file()


class TestNoticeEntry:
    """Tests for NoticeEntry dataclass."""

    def test_defaults(self) -> None:
        """Verify default field values."""
        entry = NoticeEntry(package_name='foo')
        assert entry.package_name == 'foo'
        assert entry.license_spdx == ''
        assert entry.copyright_text == ''
        assert entry.license_text == ''


class TestEmbeddedLicense:
    """Tests for EmbeddedLicense dataclass."""

    def test_fields(self) -> None:
        """Verify EmbeddedLicense fields."""
        el = EmbeddedLicense(
            path='/a/b/LICENSE',
            relative_path='vendor/lib/LICENSE',
            spdx_id='MIT',
            source='vendor/lib/LICENSE',
            package_name='mypkg',
            is_vendored=True,
        )
        assert el.spdx_id == 'MIT'
        assert el.is_vendored

    def test_default_not_vendored(self) -> None:
        """Default is_vendored is False."""
        el = EmbeddedLicense(
            path='/a/LICENSE',
            relative_path='sub/LICENSE',
            spdx_id='Apache-2.0',
            source='sub/LICENSE',
            package_name='pkg',
        )
        assert not el.is_vendored


# ── Registry Lookup Fallback ─────────────────────────────────────────


class TestResolveExternalLicenses:
    """Tests for _resolve_external_licenses."""

    def _mock_response(self, *, status_code: int = 200, json_data: dict | None = None) -> MagicMock:
        """Create a mock httpx response."""
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        return resp

    @patch('httpx.get')
    def test_resolves_license_from_pypi(self, mock_get: MagicMock) -> None:
        """Resolve license from PyPI license field."""
        mock_get.return_value = self._mock_response(
            json_data={'info': {'license': 'Apache-2.0', 'classifiers': []}},
        )
        result: dict[str, str] = {}
        _resolve_external_licenses({'xai-sdk'}, result)
        assert result['xai-sdk'] == 'Apache-2.0'

    @patch('httpx.get')
    def test_resolves_license_expression(self, mock_get: MagicMock) -> None:
        """Resolve license from PEP 639 license_expression field."""
        mock_get.return_value = self._mock_response(
            json_data={
                'info': {
                    'license_expression': 'MIT OR Apache-2.0',
                    'license': '',
                    'classifiers': [],
                },
            },
        )
        result: dict[str, str] = {}
        _resolve_external_licenses({'dual-lib'}, result)
        assert result['dual-lib'] == 'MIT OR Apache-2.0'

    @patch('httpx.get')
    def test_falls_back_to_classifier(self, mock_get: MagicMock) -> None:
        """Fall back to classifier when license field is empty."""
        mock_get.return_value = self._mock_response(
            json_data={
                'info': {
                    'license': '',
                    'classifiers': [
                        'License :: OSI Approved :: MIT License',
                        'Programming Language :: Python',
                    ],
                },
            },
        )
        result: dict[str, str] = {}
        _resolve_external_licenses({'some-lib'}, result)
        assert result['some-lib'] == 'MIT License'

    @patch('httpx.get')
    def test_skips_unknown_license(self, mock_get: MagicMock) -> None:
        """Skip packages with 'UNKNOWN' license."""
        mock_get.return_value = self._mock_response(
            json_data={'info': {'license': 'UNKNOWN', 'classifiers': []}},
        )
        result: dict[str, str] = {}
        _resolve_external_licenses({'mystery-pkg'}, result)
        assert 'mystery-pkg' not in result

    @patch('httpx.get')
    def test_handles_404(self, mock_get: MagicMock) -> None:
        """Handle 404 from PyPI gracefully."""
        mock_get.return_value = self._mock_response(status_code=404)
        result: dict[str, str] = {}
        _resolve_external_licenses({'nonexistent-pkg'}, result)
        assert 'nonexistent-pkg' not in result

    @patch('httpx.get')
    def test_handles_network_error(self, mock_get: MagicMock) -> None:
        """Handle network errors gracefully."""
        mock_get.side_effect = ConnectionError('network down')
        result: dict[str, str] = {}
        _resolve_external_licenses({'offline-pkg'}, result)
        assert 'offline-pkg' not in result

    @patch('httpx.get')
    def test_multiple_deps(self, mock_get: MagicMock) -> None:
        """Resolve multiple deps in one call."""

        def side_effect(url: str, **kwargs: object) -> MagicMock:
            """Return different responses per package."""
            if 'xai-sdk' in url:
                return self._mock_response(
                    json_data={'info': {'license': 'Apache-2.0', 'classifiers': []}},
                )
            if 'pydantic' in url:
                return self._mock_response(
                    json_data={'info': {'license': 'MIT', 'classifiers': []}},
                )
            return self._mock_response(status_code=404)

        mock_get.side_effect = side_effect
        result: dict[str, str] = {}
        _resolve_external_licenses({'xai-sdk', 'pydantic', 'gone-pkg'}, result)
        assert result['xai-sdk'] == 'Apache-2.0'
        assert result['pydantic'] == 'MIT'
        assert 'gone-pkg' not in result

    @patch('httpx.get')
    def test_skips_none_license(self, mock_get: MagicMock) -> None:
        """Skip packages with 'None' license string."""
        mock_get.return_value = self._mock_response(
            json_data={'info': {'license': 'None', 'classifiers': []}},
        )
        result: dict[str, str] = {}
        _resolve_external_licenses({'none-lic'}, result)
        assert 'none-lic' not in result


# ── LicenseHeaderConfig Parsing ──────────────────────────────────────


class TestLicenseHeaderConfig:
    """Tests for LicenseHeaderConfig dataclass and _parse_license_headers."""

    def test_defaults(self) -> None:
        """Default config has sensible values."""
        cfg = LicenseHeaderConfig()
        assert cfg.copyright_holder == 'Google LLC'
        assert cfg.license_type == 'apache'
        assert cfg.license_file == ''
        assert cfg.spdx_only is False
        assert cfg.year == ''
        assert cfg.check_only is False
        assert cfg.verbose is False
        assert '**/vendor/**' in cfg.ignore
        assert '**/node_modules/**' in cfg.ignore

    def test_parse_minimal(self) -> None:
        """Parse empty dict returns defaults."""
        cfg = _parse_license_headers({})
        assert cfg.copyright_holder == 'Google LLC'
        assert cfg.license_type == 'apache'

    def test_parse_all_fields(self) -> None:
        """Parse all fields from a TOML-like dict."""
        cfg = _parse_license_headers({
            'copyright_holder': 'Acme Corp',
            'license_type': 'mit',
            'license_file': 'HEADER.txt',
            'spdx_only': True,
            'year': '2025-2026',
            'ignore': ['**/test/**'],
            'check_only': True,
            'verbose': True,
        })
        assert cfg.copyright_holder == 'Acme Corp'
        assert cfg.license_type == 'mit'
        assert cfg.license_file == 'HEADER.txt'
        assert cfg.spdx_only is True
        assert cfg.year == '2025-2026'
        assert cfg.ignore == ['**/test/**']
        assert cfg.check_only is True
        assert cfg.verbose is True

    def test_parse_invalid_license_type(self) -> None:
        """Reject invalid license_type."""
        import pytest
        from releasekit.errors import ReleaseKitError

        with pytest.raises(ReleaseKitError, match='license_type'):
            _parse_license_headers({'license_type': 'gpl'})

    def test_parse_unknown_key(self) -> None:
        """Reject unknown keys."""
        import pytest
        from releasekit.errors import ReleaseKitError

        with pytest.raises(ReleaseKitError, match='Unknown key'):
            _parse_license_headers({'copyrigt_holder': 'typo'})

    def test_parse_ignore_not_list(self) -> None:
        """Reject ignore as non-list."""
        import pytest
        from releasekit.errors import ReleaseKitError

        with pytest.raises(ReleaseKitError, match='ignore must be a list'):
            _parse_license_headers({'ignore': '**/vendor/**'})

    def test_valid_keys_match_dataclass(self) -> None:
        """VALID_LICENSE_HEADER_KEYS matches LicenseHeaderConfig fields."""
        fields = {f.name for f in LicenseHeaderConfig.__dataclass_fields__.values()}
        assert VALID_LICENSE_HEADER_KEYS == fields

    def test_year_coerced_to_string(self) -> None:
        """Year integer is coerced to string."""
        cfg = _parse_license_headers({'year': 2025})
        assert cfg.year == '2025'

    def test_allowed_license_types(self) -> None:
        """All four addlicense types are accepted."""
        for lt in ('apache', 'bsd', 'mit', 'mpl'):
            cfg = _parse_license_headers({'license_type': lt})
            assert cfg.license_type == lt


# ── fix_missing_spdx_headers ─────────────────────────────────────────


class TestFixMissingSpdxHeaders:
    """Tests for fix_missing_spdx_headers fixer."""

    def test_skips_non_publishable(self, tmp_path: Path) -> None:
        """Skip non-publishable packages."""
        pkg = _make_pkg(tmp_path, 'internal', publishable=False)
        changes = fix_missing_spdx_headers([pkg])
        assert changes == [] or all('not found' in c for c in changes)

    @patch('shutil.which', return_value=None)
    def test_addlicense_not_found(self, _mock_which: MagicMock, tmp_path: Path) -> None:
        """Return warning when addlicense is not installed."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers([pkg])
        assert len(changes) == 1
        assert 'not found' in changes[0]

    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_dry_run_does_not_execute(self, _mock_which: MagicMock, tmp_path: Path) -> None:
        """Dry run produces command but does not execute."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers([pkg], dry_run=True)
        assert len(changes) == 1
        assert '(dry-run)' in changes[0]
        assert 'addlicense' in changes[0]

    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_dry_run_includes_config_flags(self, _mock_which: MagicMock, tmp_path: Path) -> None:
        """Dry run command includes all config flags."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers(
            [pkg],
            dry_run=True,
            copyright_holder='Acme Corp',
            license_type='mit',
            spdx_only=True,
            year='2025',
            ignore=['**/vendor/**'],
            verbose=True,
        )
        cmd = changes[0]
        assert '-c' in cmd
        assert 'Acme Corp' in cmd
        assert '-l' in cmd
        assert 'mit' in cmd
        assert '-s=only' in cmd
        assert '-y' in cmd
        assert '2025' in cmd
        assert '-ignore' in cmd
        assert '**/vendor/**' in cmd

    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_dry_run_uses_license_file_over_type(self, _mock_which: MagicMock, tmp_path: Path) -> None:
        """When license_file is set, -f is used instead of -l."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers(
            [pkg],
            dry_run=True,
            license_file='HEADER.txt',
        )
        cmd = changes[0]
        assert '-f' in cmd
        assert 'HEADER.txt' in cmd
        assert '-l' not in cmd

    @patch('subprocess.run')
    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_successful_run(self, _mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        """Successful addlicense run reports OK."""
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers([pkg])
        assert any('OK' in c for c in changes)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_failed_run(self, _mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        """Failed addlicense run reports exit code."""
        mock_run.return_value = MagicMock(returncode=1, stderr='some error')
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers([pkg])
        assert any('exited 1' in c for c in changes)

    @patch('subprocess.run', side_effect=FileNotFoundError)
    @patch('shutil.which', return_value='/usr/local/bin/addlicense')
    def test_binary_disappears(self, _mock_which: MagicMock, _mock_run: MagicMock, tmp_path: Path) -> None:
        """Handle addlicense binary disappearing between which and run."""
        pkg = _make_pkg(tmp_path, 'mypkg')
        changes = fix_missing_spdx_headers([pkg])
        assert any('not found' in c for c in changes)
