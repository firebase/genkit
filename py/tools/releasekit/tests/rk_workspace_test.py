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

"""Tests for releasekit.workspace module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.workspace import Package, discover_packages


def _write_root(
    root: Path,
    members: str = '"packages/*"',
    exclude: str = '',
    sources: str = '',
) -> None:
    """Write a minimal root pyproject.toml with workspace config."""
    exclude_line = f'exclude = [{exclude}]' if exclude else ''
    sources_section = f'\n[tool.uv.sources]\n{sources}\n' if sources else ''
    (root / 'pyproject.toml').write_text(
        f'[project]\nname = "workspace"\n\n'
        f'[tool.uv.workspace]\nmembers = [{members}]\n{exclude_line}\n'
        f'{sources_section}'
    )


def _write_package(root: Path, subdir: str, name: str, version: str = '0.1.0', deps: str = '') -> Path:
    """Write a minimal package pyproject.toml."""
    pkg_dir = root / subdir
    pkg_dir.mkdir(parents=True, exist_ok=True)
    deps_line = f'dependencies = [{deps}]' if deps else 'dependencies = []'
    (pkg_dir / 'pyproject.toml').write_text(f'[project]\nname = "{name}"\nversion = "{version}"\n{deps_line}\n')
    return pkg_dir


class TestDiscoverPackagesBasic:
    """discover_packages finds packages from member globs."""

    def test_single_package(self, tmp_path: Path) -> None:
        """A single workspace member is discovered."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'my-core', '1.0.0')
        pkgs = discover_packages(tmp_path)
        assert len(pkgs) == 1, f'Expected 1 package, got {len(pkgs)}'
        assert pkgs[0].name == 'my-core', f'Expected my-core, got {pkgs[0].name}'
        assert pkgs[0].version == '1.0.0', f'Expected 1.0.0, got {pkgs[0].version}'

    def test_multiple_packages(self, tmp_path: Path) -> None:
        """Multiple member globs discover packages from all matching dirs."""
        _write_root(tmp_path, '"packages/*", "plugins/*"')
        _write_package(tmp_path, 'packages/core', 'core')
        _write_package(tmp_path, 'plugins/auth', 'plugin-auth')
        pkgs = discover_packages(tmp_path)
        names = [p.name for p in pkgs]
        assert sorted(names) == ['core', 'plugin-auth'], f'Expected [core, plugin-auth], got {names}'

    def test_sorted_by_name(self, tmp_path: Path) -> None:
        """Packages are returned sorted by name."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/zebra', 'zebra')
        _write_package(tmp_path, 'packages/alpha', 'alpha')
        pkgs = discover_packages(tmp_path)
        names = [p.name for p in pkgs]
        assert names == ['alpha', 'zebra'], f'Expected sorted, got {names}'


class TestDiscoverPackagesDeps:
    """discover_packages classifies internal vs external dependencies."""

    def test_internal_dep(self, tmp_path: Path) -> None:
        """Deps matching workspace packages with workspace=true source are internal."""
        _write_root(tmp_path, sources='genkit = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'genkit', '0.5.0')
        _write_package(
            tmp_path,
            'packages/plugin',
            'genkit-plugin-foo',
            '0.5.0',
            deps='"genkit>=0.5.0"',
        )
        pkgs = discover_packages(tmp_path)
        plugin = next(p for p in pkgs if p.name == 'genkit-plugin-foo')
        assert plugin.internal_deps == ['genkit'], f'Expected internal dep genkit, got {plugin.internal_deps}'

    def test_pinned_dep_is_external(self, tmp_path: Path) -> None:
        """Workspace member deps without workspace=true in sources are external.

        If a package depends on a workspace member but that member is NOT
        listed with ``workspace = true`` in ``[tool.uv.sources]``, it's
        pinned to a PyPI version and excluded from the release graph.
        """
        # No sources entry for genkit → it's pinned to PyPI.
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'genkit', '1.0.0')
        _write_package(
            tmp_path,
            'packages/app-legacy',
            'app-legacy',
            '0.1.0',
            deps='"genkit==1.0.0"',
        )
        pkgs = discover_packages(tmp_path)
        app = next(p for p in pkgs if p.name == 'app-legacy')
        # genkit is a workspace member, but NOT workspace-sourced.
        # So it should be classified as external, not internal.
        assert app.internal_deps == [], f'Expected no internal deps, got {app.internal_deps}'
        assert 'genkit' in app.external_deps, f'Expected genkit in external deps, got {app.external_deps}'

    def test_external_dep(self, tmp_path: Path) -> None:
        """Deps not in the workspace are classified as external."""
        _write_root(tmp_path)
        _write_package(
            tmp_path,
            'packages/core',
            'my-pkg',
            deps='"requests>=2.28.0"',
        )
        pkgs = discover_packages(tmp_path)
        assert pkgs[0].external_deps == ['requests'], f'Expected external dep requests, got {pkgs[0].external_deps}'

    def test_mixed_deps(self, tmp_path: Path) -> None:
        """Both internal and external deps are classified correctly."""
        _write_root(tmp_path, sources='core = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'core')
        _write_package(
            tmp_path,
            'packages/app',
            'app',
            deps='"core", "httpx>=0.27"',
        )
        pkgs = discover_packages(tmp_path)
        app = next(p for p in pkgs if p.name == 'app')
        assert app.internal_deps == ['core'], f'Expected internal: [core], got {app.internal_deps}'
        assert app.external_deps == ['httpx'], f'Expected external: [httpx], got {app.external_deps}'


class TestDiscoverPackagesExclude:
    """discover_packages respects exclusion patterns."""

    def test_workspace_exclude(self, tmp_path: Path) -> None:
        """Packages matching workspace exclude globs are excluded."""
        _write_root(tmp_path, '"packages/*"', '"packages/test"')
        _write_package(tmp_path, 'packages/real', 'real-pkg')
        _write_package(tmp_path, 'packages/test', 'test-pkg')
        pkgs = discover_packages(tmp_path)
        names = [p.name for p in pkgs]
        assert 'test-pkg' not in names, f'Expected test-pkg excluded, got {names}'

    def test_additional_exclude(self, tmp_path: Path) -> None:
        """Additional exclude_patterns filter by package name."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'core')
        _write_package(tmp_path, 'packages/sample', 'sample-demo')
        pkgs = discover_packages(tmp_path, exclude_patterns=['sample-*'])
        names = [p.name for p in pkgs]
        assert 'sample-demo' not in names, f'Expected sample-demo excluded, got {names}'


class TestDiscoverPackagesErrors:
    """discover_packages raises clear errors on workspace issues."""

    def test_missing_pyproject(self, tmp_path: Path) -> None:
        """Missing root pyproject.toml raises RK-WORKSPACE-NOT-FOUND."""
        with pytest.raises(ReleaseKitError) as exc_info:
            discover_packages(tmp_path)
        assert 'RK-WORKSPACE-NOT-FOUND' in str(exc_info.value), f'Expected RK-WORKSPACE-NOT-FOUND, got {exc_info.value}'

    def test_no_members(self, tmp_path: Path) -> None:
        """Empty members list raises RK-WORKSPACE-NO-MEMBERS."""
        _write_root(tmp_path, members='')
        with pytest.raises(ReleaseKitError) as exc_info:
            discover_packages(tmp_path)
        assert 'RK-WORKSPACE-NO-MEMBERS' in str(exc_info.value), (
            f'Expected RK-WORKSPACE-NO-MEMBERS, got {exc_info.value}'
        )

    def test_duplicate_package_name(self, tmp_path: Path) -> None:
        """Duplicate package names raise RK-WORKSPACE-DUPLICATE-PACKAGE."""
        _write_root(tmp_path, members='"a", "b"')
        _write_package(tmp_path, 'a', 'dup-pkg', '1.0.0')
        _write_package(tmp_path, 'b', 'dup-pkg', '2.0.0')
        with pytest.raises(ReleaseKitError) as exc_info:
            discover_packages(tmp_path)
        assert 'RK-WORKSPACE-DUPLICATE-PACKAGE' in str(exc_info.value), (
            f'Expected RK-WORKSPACE-DUPLICATE-PACKAGE, got {exc_info.value}'
        )


class TestDiscoverPackagesNameNormalization:
    """Package names are normalized per PEP 503."""

    def test_underscore_to_hyphen(self, tmp_path: Path) -> None:
        """Underscores in package names are converted to hyphens."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/my_pkg', 'my_pkg')
        pkgs = discover_packages(tmp_path)
        assert pkgs[0].name == 'my-pkg', f'Expected my-pkg, got {pkgs[0].name}'

    def test_dep_normalization(self, tmp_path: Path) -> None:
        """Dependency names are normalized for matching."""
        _write_root(tmp_path, sources='my_core = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'my_core')
        _write_package(
            tmp_path,
            'packages/app',
            'my-app',
            deps='"my_core>=1.0"',
        )
        pkgs = discover_packages(tmp_path)
        app = next(p for p in pkgs if p.name == 'my-app')
        assert app.internal_deps == ['my-core'], f'Expected normalized dep my-core, got {app.internal_deps}'


class TestPackageDataclass:
    """Package dataclass behaves correctly."""

    def test_is_frozen(self, tmp_path: Path) -> None:
        """Package instances are immutable."""
        pkg = Package(
            name='test',
            version='1.0.0',
            path=tmp_path,
            manifest_path=tmp_path / 'pyproject.toml',
        )
        with pytest.raises(AttributeError):
            pkg.name = 'oops'  # type: ignore[misc]

    def test_default_publishable(self, tmp_path: Path) -> None:
        """Packages are publishable by default."""
        pkg = Package(
            name='test',
            version='1.0.0',
            path=tmp_path,
            manifest_path=tmp_path / 'pyproject.toml',
        )
        assert pkg.is_publishable is True, f'Expected is_publishable=True, got {pkg.is_publishable}'


class TestDiscoverPackagesParseErrors:
    """Tests for workspace parse error handling."""

    def test_corrupt_root_toml(self, tmp_path: Path) -> None:
        """Corrupt root pyproject.toml raises ReleaseKitError."""
        (tmp_path / 'pyproject.toml').write_text('not valid toml {{{{')
        with pytest.raises(ReleaseKitError):
            discover_packages(tmp_path)

    def test_no_name_in_package(self, tmp_path: Path) -> None:
        """Package without [project].name raises ReleaseKitError."""
        _write_root(tmp_path)
        pkg_dir = tmp_path / 'packages' / 'bad'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text('[project]\nversion = "1.0.0"\n')
        with pytest.raises(ReleaseKitError, match='No \\[project\\].name'):
            discover_packages(tmp_path)

    def test_corrupt_package_toml(self, tmp_path: Path) -> None:
        """Corrupt package pyproject.toml raises ReleaseKitError."""
        _write_root(tmp_path)
        pkg_dir = tmp_path / 'packages' / 'bad'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text('not valid {{{{')
        with pytest.raises(ReleaseKitError):
            discover_packages(tmp_path)

    def test_no_matching_members(self, tmp_path: Path) -> None:
        """No directories matching member globs raises RK-WORKSPACE-NO-MEMBERS."""
        _write_root(tmp_path, members='"nonexistent/*"')
        with pytest.raises(ReleaseKitError, match='No packages found'):
            discover_packages(tmp_path)


class TestDiscoverPackagesPrivate:
    """Tests for private package detection."""

    def test_private_package_not_publishable(self, tmp_path: Path) -> None:
        """Package with Private :: Do Not Upload classifier is not publishable."""
        _write_root(tmp_path)
        pkg_dir = tmp_path / 'packages' / 'internal'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\n'
            'name = "internal-tool"\n'
            'version = "0.1.0"\n'
            'dependencies = []\n'
            'classifiers = ["Private :: Do Not Upload"]\n',
        )
        pkgs = discover_packages(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0].is_publishable is False


class TestDiscoverPackagesMalformedDeps:
    """Tests for malformed dependency specifier fallback."""

    def test_malformed_dep_uses_fallback(self, tmp_path: Path) -> None:
        """Malformed dep specifier uses regex fallback for name extraction."""
        _write_root(tmp_path)
        pkg_dir = tmp_path / 'packages' / 'app'
        pkg_dir.mkdir(parents=True)
        # Write a dep with a malformed specifier that packaging can't parse.
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "app"\nversion = "1.0.0"\ndependencies = ["some-pkg [bad"]\n',
        )
        # Should not crash — fallback extracts name.
        pkgs = discover_packages(tmp_path)
        assert len(pkgs) == 1
        assert 'some-pkg' in pkgs[0].external_deps or 'some-pkg [bad' in pkgs[0].all_deps


class TestDiscoverPackagesReadErrors:
    """Tests for file read/parse error paths."""

    def test_unreadable_package_pyproject(self, tmp_path: Path) -> None:
        """Unreadable package pyproject.toml raises ReleaseKitError."""
        _write_root(tmp_path)
        pkg_dir = tmp_path / 'packages' / 'broken'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "broken"\nversion = "0.1.0"\ndependencies = []\n')
        # Make unreadable.
        pyproject.chmod(0o000)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Failed to read'):
                discover_packages(tmp_path)
        finally:
            pyproject.chmod(0o644)  # noqa: S103

    def test_unreadable_root_pyproject(self, tmp_path: Path) -> None:
        """Unreadable root pyproject.toml raises ReleaseKitError."""
        _write_root(tmp_path)
        root_pyproject = tmp_path / 'pyproject.toml'
        root_pyproject.chmod(0o000)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Failed to read'):
                discover_packages(tmp_path)
        finally:
            root_pyproject.chmod(0o644)  # noqa: S103

    def test_js_ecosystem_dispatch(self, tmp_path: Path) -> None:
        """JS ecosystem dispatches to _discover_js_packages."""
        with patch('releasekit.workspace._discover_js_packages', return_value=[]) as mock_js:
            result = discover_packages(tmp_path, ecosystem='js')
        assert result == []
        mock_js.assert_called_once()
