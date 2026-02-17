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

"""End-to-end tests for the license compatibility check."""

from __future__ import annotations

import json
from pathlib import Path

from releasekit.checks._universal import LicenseExemptions, _check_license_compatibility
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package


def _make_pkg(
    tmp_path: Path,
    name: str,
    license_value: str = '',
    *,
    is_publishable: bool = True,
    internal_deps: list[str] | None = None,
    external_deps: list[str] | None = None,
) -> Package:
    """Create a fake package directory with a pyproject.toml."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(exist_ok=True)
    manifest = pkg_dir / 'pyproject.toml'
    if license_value:
        manifest.write_text(f'[project]\nname = "{name}"\nlicense = "{license_value}"\n')
    else:
        manifest.write_text(f'[project]\nname = "{name}"\n')
    return Package(
        name=name,
        version='1.0.0',
        path=pkg_dir,
        manifest_path=manifest,
        internal_deps=internal_deps or [],
        external_deps=external_deps or [],
        all_deps=(internal_deps or []) + (external_deps or []),
        is_publishable=is_publishable,
    )


# ── All compatible ───────────────────────────────────────────────────


class TestAllCompatible:
    """Tests for all Compatible."""

    def test_permissive_deps_pass(self, tmp_path: Path) -> None:
        """Test permissive deps pass."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a', 'lib-b'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        lib_b = _make_pkg(tmp_path, 'lib-b', 'BSD-3-Clause')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a, lib_b],
            result,
            project_license='Apache-2.0',
        )
        assert 'license_compatibility' in result.passed

    def test_gpl3_with_permissive_deps(self, tmp_path: Path) -> None:
        """Test gpl3 with permissive deps."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='GPL-3.0-only',
        )
        assert 'license_compatibility' in result.passed


# ── Violations detected ─────────────────────────────────────────────


class TestViolations:
    """Tests for violations."""

    def test_mit_depending_on_gpl3(self, tmp_path: Path) -> None:
        """Test mit depending on gpl3."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib'],
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed
        assert 'gpl-lib' in result.errors['license_compatibility']

    def test_gpl2_depending_on_apache(self, tmp_path: Path) -> None:
        """Test gpl2 depending on apache."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-2.0-only',
            internal_deps=['apache-lib'],
        )
        apache_lib = _make_pkg(tmp_path, 'apache-lib', 'Apache-2.0')
        result = PreflightResult()
        _check_license_compatibility(
            [app, apache_lib],
            result,
            project_license='GPL-2.0-only',
        )
        assert 'license_compatibility' in result.failed

    def test_multiple_violations(self, tmp_path: Path) -> None:
        """Test multiple violations."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib', 'agpl-lib'],
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib, agpl_lib],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed
        msg = result.errors['license_compatibility']
        assert 'gpl-lib' in msg
        assert 'agpl-lib' in msg


# ── Auto-detection of project license ────────────────────────────────


class TestAutoDetection:
    """Tests for auto Detection."""

    def test_detects_from_first_publishable(self, tmp_path: Path) -> None:
        """Test detects from first publishable."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        # No project_license override — should auto-detect Apache-2.0.
        _check_license_compatibility([app, lib_a], result)
        assert 'license_compatibility' in result.passed

    def test_warns_when_no_license_found(self, tmp_path: Path) -> None:
        """Test warns when no license found."""
        app = _make_pkg(tmp_path, 'myapp', '')
        result = PreflightResult()
        _check_license_compatibility([app], result)
        assert 'license_compatibility' in result.warnings
        assert 'Could not determine' in result.warning_messages['license_compatibility']


# ── Unknown project license ──────────────────────────────────────────


class TestUnknownLicense:
    """Tests for unknown License."""

    def test_warns_on_unknown_project_license(self, tmp_path: Path) -> None:
        """Test warns on unknown project license."""
        app = _make_pkg(tmp_path, 'myapp', 'Apache-2.0')
        result = PreflightResult()
        _check_license_compatibility(
            [app],
            result,
            project_license='NoSuchLicense-99',
        )
        assert 'license_compatibility' in result.warnings
        assert 'Unknown project license' in result.warning_messages['license_compatibility']


# ── Unresolved dependency licenses ───────────────────────────────────


class TestUnresolvedDeps:
    """Tests for unresolved Deps."""

    def test_unresolved_dep_license_is_incompatible(self, tmp_path: Path) -> None:
        """Unresolvable license strings are treated as incompatible."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['weird-lib'],
        )
        weird_lib = _make_pkg(tmp_path, 'weird-lib', 'xyzzy-custom-9999')
        result = PreflightResult()
        _check_license_compatibility(
            [app, weird_lib],
            result,
            project_license='Apache-2.0',
        )
        assert 'license_compatibility' in result.failed
        assert 'weird-lib' in result.errors['license_compatibility']


# ── Non-publishable packages skipped ─────────────────────────────────


class TestNonPublishable:
    """Tests for non Publishable."""

    def test_non_publishable_deps_not_checked(self, tmp_path: Path) -> None:
        """Test non publishable deps not checked."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['internal-tool'],
        )
        # internal-tool has GPL but is not publishable — should not trigger.
        tool = _make_pkg(
            tmp_path,
            'internal-tool',
            'GPL-3.0-only',
            is_publishable=False,
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, tool],
            result,
            project_license='MIT',
        )
        # The dep license is still checked (it's a dep of a publishable pkg),
        # but the non-publishable pkg itself is not checked as a "project".
        # Since MIT can't depend on GPL-3.0, this should still fail.
        assert 'license_compatibility' in result.failed


# ── External deps ────────────────────────────────────────────────────


class TestExternalDeps:
    """Tests for external Deps."""

    def test_external_dep_checked(self, tmp_path: Path) -> None:
        """Test external dep checked."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            external_deps=['gpl-ext'],
        )
        gpl_ext = _make_pkg(tmp_path, 'gpl-ext', 'GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_ext],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed


# ── JS package detection ─────────────────────────────────────────────


class TestJsPackageDetection:
    """Tests for js Package Detection."""

    def test_js_license_detected(self, tmp_path: Path) -> None:
        """Test js license detected."""
        app_dir = tmp_path / 'myapp'
        app_dir.mkdir()
        (app_dir / 'package.json').write_text(json.dumps({'name': 'myapp', 'license': 'MIT'}))
        app = Package(
            name='myapp',
            version='1.0.0',
            path=app_dir,
            manifest_path=app_dir / 'package.json',
            internal_deps=['dep'],
            external_deps=[],
            all_deps=['dep'],
            is_publishable=True,
        )
        dep_dir = tmp_path / 'dep'
        dep_dir.mkdir()
        (dep_dir / 'package.json').write_text(json.dumps({'name': 'dep', 'license': 'ISC'}))
        dep = Package(
            name='dep',
            version='1.0.0',
            path=dep_dir,
            manifest_path=dep_dir / 'package.json',
            internal_deps=[],
            external_deps=[],
            all_deps=[],
            is_publishable=True,
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, dep],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.passed


# ── Exempt packages (commercial licenses) ────────────────────────────


class TestExemptPackages:
    """Tests for exempt Packages."""

    def test_exempt_package_skipped(self, tmp_path: Path) -> None:
        """Commercially-licensed deps can be exempted by name."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['oracle-jdbc'],
        )
        oracle = _make_pkg(tmp_path, 'oracle-jdbc', 'Proprietary')
        ex = LicenseExemptions(exempt_packages=frozenset({'oracle-jdbc'}))
        result = PreflightResult()
        _check_license_compatibility(
            [app, oracle],
            result,
            project_license='MIT',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_non_exempt_still_fails(self, tmp_path: Path) -> None:
        """Only named exemptions are skipped."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib'],
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        ex = LicenseExemptions(exempt_packages=frozenset({'other-pkg'}))
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib],
            result,
            project_license='MIT',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.failed


# ── Allow-list (global license allow) ────────────────────────────────


class TestAllowLicenses:
    """Tests for allow Licenses."""

    def test_allowed_license_passes(self, tmp_path: Path) -> None:
        """Globally allowed licenses bypass graph checks."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['sspl-lib'],
        )
        sspl_lib = _make_pkg(tmp_path, 'sspl-lib', 'SSPL-1.0')
        ex = LicenseExemptions(allow_licenses=frozenset({'SSPL-1.0'}))
        result = PreflightResult()
        _check_license_compatibility(
            [app, sspl_lib],
            result,
            project_license='MIT',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_non_allowed_still_fails(self, tmp_path: Path) -> None:
        """Test non allowed still fails."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib'],
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        ex = LicenseExemptions(allow_licenses=frozenset({'SSPL-1.0'}))
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib],
            result,
            project_license='MIT',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.failed


# ── License overrides ────────────────────────────────────────────────


class TestLicenseOverrides:
    """Tests for license Overrides."""

    def test_override_fixes_wrong_detection(self, tmp_path: Path) -> None:
        """Override a dep's detected license to the correct one."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['misdetected-lib'],
        )
        # Detected as GPL but actually MIT (wrong LICENSE file).
        misdetected = _make_pkg(tmp_path, 'misdetected-lib', 'GPL-3.0-only')
        ex = LicenseExemptions(license_overrides={'misdetected-lib': 'MIT'})
        result = PreflightResult()
        _check_license_compatibility(
            [app, misdetected],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_override_with_spdx_expression(self, tmp_path: Path) -> None:
        """Override can be a full SPDX expression."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['dual-lib'],
        )
        dual = _make_pkg(tmp_path, 'dual-lib', 'GPL-3.0-only')
        ex = LicenseExemptions(
            license_overrides={'dual-lib': 'MIT OR GPL-3.0-only'},
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, dual],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        # MIT branch of "MIT OR GPL-3.0-only" is compatible with Apache-2.0.
        assert 'license_compatibility' in result.passed


# ── Dual-licensed dependencies (SPDX OR expressions) ────────────────


class TestDualLicensed:
    """Tests for dual Licensed."""

    def test_or_expression_passes_if_either_branch_compatible(
        self,
        tmp_path: Path,
    ) -> None:
        """A dep licensed 'MIT OR GPL-3.0-only' is compatible with Apache-2.0."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['dual-lib'],
        )
        dual = _make_pkg(tmp_path, 'dual-lib', 'MIT OR GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, dual],
            result,
            project_license='Apache-2.0',
        )
        assert 'license_compatibility' in result.passed

    def test_and_expression_fails_if_any_branch_incompatible(
        self,
        tmp_path: Path,
    ) -> None:
        """A dep licensed 'MIT AND GPL-3.0-only' requires both to be compat."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['conjunctive-lib'],
        )
        conj = _make_pkg(tmp_path, 'conjunctive-lib', 'MIT AND GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, conj],
            result,
            project_license='MIT',
        )
        # MIT can't depend on GPL-3.0-only, so the AND fails.
        assert 'license_compatibility' in result.failed

    def test_or_expression_both_incompatible_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """If neither branch of OR is compatible, it fails."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['copyleft-lib'],
        )
        copyleft = _make_pkg(
            tmp_path,
            'copyleft-lib',
            'GPL-3.0-only OR AGPL-3.0-only',
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, copyleft],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed


# ── Combined exemptions ──────────────────────────────────────────────


class TestCombinedExemptions:
    """Tests for combined Exemptions."""

    def test_exempt_and_override_together(self, tmp_path: Path) -> None:
        """Test exempt and override together."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['commercial-sdk', 'misdetected-lib'],
        )
        sdk = _make_pkg(tmp_path, 'commercial-sdk', 'Proprietary')
        misdetected = _make_pkg(tmp_path, 'misdetected-lib', 'GPL-3.0-only')
        ex = LicenseExemptions(
            exempt_packages=frozenset({'commercial-sdk'}),
            license_overrides={'misdetected-lib': 'BSD-3-Clause'},
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, sdk, misdetected],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed


# ── Deny-list (blocked licenses) ─────────────────────────────────────


class TestDenyLicenses:
    """Tests for deny Licenses."""

    def test_denied_license_fails(self, tmp_path: Path) -> None:
        """A dep with a denied license is a hard failure."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only', 'SSPL-1.0'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.failed
        assert 'blocked' in result.errors['license_compatibility']
        assert 'AGPL-3.0-only' in result.errors['license_compatibility']

    def test_denied_even_if_graph_compatible(self, tmp_path: Path) -> None:
        """Deny-list overrides graph compatibility."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='GPL-3.0-only',
            exemptions=ex,
        )
        # AGPL-3.0 is graph-compatible with GPL-3.0, but denied.
        assert 'license_compatibility' in result.failed

    def test_non_denied_license_passes(self, tmp_path: Path) -> None:
        """Licenses not in the deny-list are unaffected."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['mit-lib'],
        )
        mit_lib = _make_pkg(tmp_path, 'mit-lib', 'MIT')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, mit_lib],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_deny_in_or_expression(self, tmp_path: Path) -> None:
        """If any leaf ID in an OR expression is denied, it fails."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['dual-lib'],
        )
        dual = _make_pkg(tmp_path, 'dual-lib', 'MIT OR AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, dual],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.failed

    def test_exempt_package_bypasses_deny(self, tmp_path: Path) -> None:
        """Exempt packages skip the deny check too."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
            exempt_packages=frozenset({'agpl-lib'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed


# ── Project-level exceptions to deny-list ────────────────────────────


class TestProjectExceptions:
    """Tests for project Exceptions."""

    def test_project_exception_overrides_deny(self, tmp_path: Path) -> None:
        """A per-project exception removes a license from the deny-list."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only', 'SSPL-1.0'}),
            project_exceptions={
                'agpl-lib': frozenset({'AGPL-3.0-only'}),
            },
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        # AGPL-3.0-only is denied globally but excepted for agpl-lib.
        # It still needs to pass the compatibility check (Phase 2).
        # Apache-2.0 can't depend on AGPL-3.0-only, so it fails compat.
        assert 'license_compatibility' in result.failed
        # But the failure should be a compat failure, not a deny failure.
        assert 'blocked' not in result.errors['license_compatibility']

    def test_project_exception_passes_when_also_compatible(
        self,
        tmp_path: Path,
    ) -> None:
        """Exception + graph-compatible = pass."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
            project_exceptions={
                'agpl-lib': frozenset({'AGPL-3.0-only'}),
            },
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='GPL-3.0-only',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_project_exception_only_for_named_package(
        self,
        tmp_path: Path,
    ) -> None:
        """Exception for pkg-A doesn't help pkg-B."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['agpl-a', 'agpl-b'],
        )
        agpl_a = _make_pkg(tmp_path, 'agpl-a', 'AGPL-3.0-only')
        agpl_b = _make_pkg(tmp_path, 'agpl-b', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
            project_exceptions={
                'agpl-a': frozenset({'AGPL-3.0-only'}),
            },
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_a, agpl_b],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        # agpl-b is still denied.
        assert 'license_compatibility' in result.failed
        assert 'agpl-b' in result.errors['license_compatibility']


# ── Workspace-level exceptions to deny-list ──────────────────────────


class TestWorkspaceExceptions:
    """Tests for workspace Exceptions."""

    def test_workspace_exception_overrides_deny(self, tmp_path: Path) -> None:
        """A workspace-wide exception removes a license from the deny-list."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['agpl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only', 'SSPL-1.0'}),
            workspace_exceptions=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib],
            result,
            project_license='GPL-3.0-only',
            exemptions=ex,
        )
        # AGPL-3.0 is denied but workspace-excepted, and GPL-3.0 is
        # graph-compatible with AGPL-3.0.
        assert 'license_compatibility' in result.passed

    def test_workspace_exception_applies_to_all_packages(
        self,
        tmp_path: Path,
    ) -> None:
        """Workspace exception covers every dep, not just one."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['agpl-a', 'agpl-b'],
        )
        agpl_a = _make_pkg(tmp_path, 'agpl-a', 'AGPL-3.0-only')
        agpl_b = _make_pkg(tmp_path, 'agpl-b', 'AGPL-3.0-only')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only'}),
            workspace_exceptions=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_a, agpl_b],
            result,
            project_license='GPL-3.0-only',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.passed

    def test_workspace_exception_does_not_cover_other_denied(
        self,
        tmp_path: Path,
    ) -> None:
        """Workspace exception for AGPL doesn't help SSPL."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['sspl-lib'],
        )
        sspl_lib = _make_pkg(tmp_path, 'sspl-lib', 'SSPL-1.0')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only', 'SSPL-1.0'}),
            workspace_exceptions=frozenset({'AGPL-3.0-only'}),
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, sspl_lib],
            result,
            project_license='Apache-2.0',
            exemptions=ex,
        )
        assert 'license_compatibility' in result.failed
        assert 'SSPL-1.0' in result.errors['license_compatibility']

    def test_workspace_and_project_exceptions_stack(
        self,
        tmp_path: Path,
    ) -> None:
        """Workspace + project exceptions combine."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'GPL-3.0-only',
            internal_deps=['agpl-lib', 'sspl-lib'],
        )
        agpl_lib = _make_pkg(tmp_path, 'agpl-lib', 'AGPL-3.0-only')
        sspl_lib = _make_pkg(tmp_path, 'sspl-lib', 'SSPL-1.0')
        ex = LicenseExemptions(
            deny_licenses=frozenset({'AGPL-3.0-only', 'SSPL-1.0'}),
            workspace_exceptions=frozenset({'AGPL-3.0-only'}),
            project_exceptions={
                'sspl-lib': frozenset({'SSPL-1.0'}),
            },
        )
        result = PreflightResult()
        _check_license_compatibility(
            [app, agpl_lib, sspl_lib],
            result,
            project_license='GPL-3.0-only',
            exemptions=ex,
        )
        # Both denied licenses are excepted. AGPL-3.0 is compat with
        # GPL-3.0. SSPL-1.0 has no compat edges → fails Phase 2.
        assert 'license_compatibility' in result.failed
        assert 'blocked' not in result.errors['license_compatibility']
