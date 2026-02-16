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

"""Tests for releasekit.preflight module."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.errors import ReleaseKitError
from releasekit.graph import build_graph
from releasekit.preflight import PreflightResult, run_preflight
from releasekit.versions import PackageVersion
from releasekit.workspace import Package
from tests._fakes import OK as _OK, FakeForge, FakePM as FakePackageManager, FakeRegistry, FakeVCS

# CI environment variables that leak into tests when running in GitHub Actions
# or other CI platforms. These must be cleared so preflight checks
# (trusted_publisher, source_integrity, build_as_code, slsa_build_level)
# don't detect a real CI environment and fail due to missing OIDC tokens.
_CI_ENV_VARS = (
    'CI',
    'GITHUB_ACTIONS',
    'GITHUB_SERVER_URL',
    'GITHUB_REPOSITORY',
    'GITHUB_SHA',
    'GITHUB_REF',
    'GITHUB_RUN_ID',
    'GITHUB_RUN_ATTEMPT',
    'GITHUB_WORKFLOW_REF',
    'RUNNER_ENVIRONMENT',
    'RUNNER_OS',
    'RUNNER_ARCH',
    'ACTIONS_ID_TOKEN_REQUEST_URL',
    'ACTIONS_ID_TOKEN_REQUEST_TOKEN',
    'GITLAB_CI',
    'CI_COMMIT_SHA',
    'CI_COMMIT_REF_NAME',
    'CI_PROJECT_URL',
    'CI_JOB_JWT_V2',
    'CI_JOB_JWT',
    'CIRCLECI',
    'CIRCLE_SHA1',
    'CIRCLE_BRANCH',
    'CIRCLE_OIDC_TOKEN_V2',
)


@pytest.fixture(autouse=True)
def _isolate_from_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove CI env vars so preflight checks don't detect a host CI environment."""
    for var in _CI_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ── PreflightResult tests ──


class TestPreflightResult:
    """Tests for PreflightResult."""

    def test_empty_result(self) -> None:
        """New result is OK with no items."""
        result = PreflightResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.passed:
            raise AssertionError('Expected no passes')
        if result.warnings:
            raise AssertionError('Expected no warnings')
        if result.failed:
            raise AssertionError('Expected no failures')

    def test_add_pass(self) -> None:
        """Passes are recorded."""
        result = PreflightResult()
        result.add_pass('test_check')
        if 'test_check' not in result.passed:
            raise AssertionError('Pass not recorded')
        if not result.ok:
            raise AssertionError('Should still be OK after pass')

    def test_add_warning(self) -> None:
        """Warnings are non-blocking."""
        result = PreflightResult()
        result.add_warning('shallow', 'Shallow clone')
        if 'shallow' not in result.warnings:
            raise AssertionError('Warning not recorded')
        if result.warning_messages.get('shallow') != 'Shallow clone':
            raise AssertionError('Warning message not stored')
        if not result.ok:
            raise AssertionError('Warnings should not fail the result')

    def test_add_failure(self) -> None:
        """Failures make result not OK."""
        result = PreflightResult()
        result.add_failure('dirty', 'Uncommitted changes')
        if 'dirty' not in result.failed:
            raise AssertionError('Failure not recorded')
        if result.errors.get('dirty') != 'Uncommitted changes':
            raise AssertionError('Error message not stored')
        if result.ok:
            raise AssertionError('Should not be OK with failures')

    def test_summary(self) -> None:
        """Summary includes counts for each category."""
        result = PreflightResult()
        result.add_pass('a')
        result.add_pass('b')
        result.add_warning('c', 'w')
        result.add_failure('d', 'f')
        summary = result.summary()
        if '4 checks' not in summary:
            raise AssertionError(f'Expected 4 checks in: {summary}')
        if '2 passed' not in summary:
            raise AssertionError(f'Expected 2 passed in: {summary}')
        if '1 warnings' not in summary:
            raise AssertionError(f'Expected 1 warnings in: {summary}')
        if '1 failed' not in summary:
            raise AssertionError(f'Expected 1 failed in: {summary}')


# ── run_preflight tests ──


class TestRunPreflight:
    """Tests for run_preflight with injected fakes."""

    def _make_packages(self, workspace_root: Path) -> list[Package]:
        """Create test packages rooted under the given workspace."""
        pkg_dir = workspace_root / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(
                name='genkit',
                version='0.5.0',
                path=pkg_dir,
                manifest_path=pkg_dir / 'pyproject.toml',
            ),
        ]

    def test_clean_workspace_passes(self, tmp_path: Path) -> None:
        """Clean workspace with no issues passes all checks."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')

    def test_dirty_worktree_fails(self, tmp_path: Path) -> None:
        """Dirty working tree raises ReleaseKitError."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        with pytest.raises(ReleaseKitError):
            asyncio.run(
                run_preflight(
                    vcs=FakeVCS(clean=False),
                    pm=FakePackageManager(),
                    forge=None,
                    registry=FakeRegistry(),
                    packages=packages,
                    graph=graph,
                    versions=versions,
                    workspace_root=tmp_path,
                ),
            )

    def test_shallow_clone_warns(self, tmp_path: Path) -> None:
        """Shallow clone produces a warning but passes."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(shallow=True),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Shallow should warn, not fail: {result.errors}')
        has_shallow_warning = any('shallow' in w.lower() for w in result.warnings)
        if not has_shallow_warning:
            raise AssertionError(f'Expected shallow warning: {result.warnings}')

    def test_skip_version_check(self, tmp_path: Path) -> None:
        """skip_version_check=True skips registry conflict check."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        # Pre-publish the version.
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.5.0', bump='none')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(published={'genkit==0.5.0'}),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                skip_version_check=True,
            ),
        )

        if not result.ok:
            raise AssertionError(f'skip_version_check should pass: {result.errors}')

    def test_forge_unavailable_warns(self, tmp_path: Path) -> None:
        """Missing forge produces a warning."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        # With forge=None, there should be a warning about forge not available.
        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')


class TestEcosystemSpecificChecks:
    """Tests for ecosystem-specific preflight checks."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        """Create test packages with pyproject.toml files."""
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.5.0"\n'
            'description = "Test"\nlicense = "Apache-2.0"\n'
            'requires-python = ">=3.10"\n'
            'authors = [{name = "Test"}]\n',
            encoding='utf-8',
        )
        return [
            Package(
                name='genkit',
                version='0.5.0',
                path=pkg_dir,
                manifest_path=pyproject,
            ),
        ]

    def test_metadata_validation_passes(self, tmp_path: Path) -> None:
        """Packages with complete metadata pass validation."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='python',
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')
        if 'metadata_validation' not in result.passed:
            raise AssertionError(f'Missing metadata_validation in passed: {result.passed}')

    def test_metadata_validation_warns_missing_fields(self, tmp_path: Path) -> None:
        """Packages with missing metadata get warnings."""
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        # Missing description, license, authors.
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.5.0"\n',
            encoding='utf-8',
        )
        packages = [
            Package(
                name='genkit',
                version='0.5.0',
                path=pkg_dir,
                manifest_path=pyproject,
            ),
        ]
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='python',
            ),
        )

        # Metadata issues are warnings, not failures.
        if not result.ok:
            raise AssertionError(f'Should still pass (warnings only): {result.errors}')
        has_metadata_warning = any('metadata_validation' in w for w in result.warnings)
        if not has_metadata_warning:
            raise AssertionError(f'Expected metadata_validation warning: {result.warnings}')

    def test_non_python_ecosystem_skips_checks(self, tmp_path: Path) -> None:
        """Non-Python ecosystems skip pip-audit and metadata checks."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='node',
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')
        if 'metadata_validation' in result.passed:
            raise AssertionError('Node ecosystem should NOT run metadata_validation')

    def test_pip_audit_skipped_when_not_enabled(self, tmp_path: Path) -> None:
        """pip-audit is not run when run_audit=False (default)."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='python',
                run_audit=False,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')
        if 'pip_audit' in result.passed:
            raise AssertionError('pip_audit should not be in passed when disabled')

    def test_non_publishable_skipped(self, tmp_path: Path) -> None:
        """Non-publishable packages are skipped in metadata check."""
        pkg_dir = tmp_path / 'packages' / 'sample'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        # Missing everything — but not publishable.
        pyproject.write_text('[project]\nname = "sample"\nversion = "0.1.0"\n', encoding='utf-8')
        packages = [
            Package(
                name='sample',
                version='0.1.0',
                path=pkg_dir,
                manifest_path=pyproject,
                is_publishable=False,
            ),
        ]
        graph = build_graph(packages)
        versions = [PackageVersion(name='sample', old_version='0.1.0', new_version='0.2.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='python',
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')
        # metadata_validation should pass because no publishable packages had issues.
        if 'metadata_validation' not in result.passed:
            raise AssertionError(f'Expected metadata_validation pass: {result.passed}')


class TestPreflightLockFile:
    """Tests for lock file preflight check."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
        ]

    def test_lock_file_out_of_date(self, tmp_path: Path) -> None:
        """Out-of-date lock file records a failure in the result."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        class FailLockPM(FakePackageManager):
            async def lock(
                self,
                *,
                check_only: bool = False,
                upgrade_package: str | None = None,
                cwd: Path | None = None,
                dry_run: bool = False,
            ) -> CommandResult:
                if check_only:
                    raise RuntimeError('Lock out of date')
                return _OK

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FailLockPM(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert not result.ok
        assert 'lock_file' in result.failed


class TestPreflightForgeAvailable:
    """Tests for forge availability check."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
        ]

    def test_forge_available_passes(self, tmp_path: Path) -> None:
        """Available forge passes the check."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=FakeForge(),
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert result.ok
        assert 'forge_available' in result.passed

    def test_forge_unavailable_warns(self, tmp_path: Path) -> None:
        """Unavailable forge CLI produces a warning."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        class UnavailableForge(FakeForge):
            async def is_available(self) -> bool:
                return False

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=UnavailableForge(),
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert result.ok  # Warning, not failure.
        assert 'forge_available' in result.warnings


class TestPreflightVersionConflicts:
    """Tests for version conflict detection."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
        ]

    def test_version_already_published(self, tmp_path: Path) -> None:
        """Version already on registry records a failure in the result."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(published={'genkit==0.6.0'}),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert not result.ok
        assert 'version_conflicts' in result.failed


class TestPreflightStaleDist:
    """Tests for stale dist/ directory detection."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
        ]

    def test_stale_dist_fails(self, tmp_path: Path) -> None:
        """Stale dist/ directory records a failure in the result."""
        packages = self._make_packages(tmp_path)
        # Create a stale dist/ directory with a file.
        dist_dir = packages[0].path / 'dist'
        dist_dir.mkdir()
        (dist_dir / 'genkit-0.5.0.tar.gz').write_text('fake')

        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert not result.ok
        assert 'dist_clean' in result.failed


class TestPreflightTrustedPublisher:
    """Tests for trusted publisher OIDC check."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
        ]

    def test_ci_without_oidc_fails(self, tmp_path: Path) -> None:
        """CI environment without OIDC is a failure (fail-closed for security)."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        env = {
            'CI': 'true',
            'GITHUB_ACTIONS': 'true',
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_REPOSITORY': 'firebase/genkit',
            'GITHUB_SHA': 'abc123',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': 'firebase/genkit/.github/workflows/release.yml@refs/heads/main',
        }
        # Ensure no OIDC env vars.
        for key in ('ACTIONS_ID_TOKEN_REQUEST_URL', 'CI_JOB_JWT_V2', 'CI_JOB_JWT', 'CIRCLE_OIDC_TOKEN_V2'):
            env.pop(key, None)

        with patch.dict(os.environ, env, clear=True):
            result = asyncio.run(
                run_preflight(
                    vcs=FakeVCS(),
                    pm=FakePackageManager(),
                    forge=None,
                    registry=FakeRegistry(),
                    packages=packages,
                    graph=graph,
                    versions=versions,
                    workspace_root=tmp_path,
                ),
            )

        assert not result.ok  # Failure, not warning — fail-closed in CI.
        assert 'trusted_publisher' in result.failed
        assert 'OIDC' in result.errors['trusted_publisher']


class TestPreflightResultHints:
    """Tests for PreflightResult hint recording."""

    def test_add_warning_with_hint(self) -> None:
        """add_warning stores hint when provided."""
        result = PreflightResult()
        result.add_warning('test_check', 'Something happened', hint='Try this fix')
        assert result.hints['test_check'] == 'Try this fix'

    def test_add_failure_with_hint(self) -> None:
        """add_failure stores hint when provided."""
        result = PreflightResult()
        result.add_failure('test_check', 'Something broke', hint='Fix it')
        assert result.hints['test_check'] == 'Fix it'
        assert not result.ok


class TestPreflightCycleDetection:
    """Tests for cycle detection in preflight."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        """Create packages with a circular dependency."""
        pkg_a = tmp_path / 'packages' / 'a'
        pkg_a.mkdir(parents=True, exist_ok=True)
        pkg_b = tmp_path / 'packages' / 'b'
        pkg_b.mkdir(parents=True, exist_ok=True)
        return [
            Package(
                name='a',
                version='0.1.0',
                path=pkg_a,
                manifest_path=pkg_a / 'pyproject.toml',
                internal_deps=['b'],
            ),
            Package(
                name='b',
                version='0.1.0',
                path=pkg_b,
                manifest_path=pkg_b / 'pyproject.toml',
                internal_deps=['a'],
            ),
        ]

    def test_cycle_detected_fails(self, tmp_path: Path) -> None:
        """Circular dependency records a failure."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [
            PackageVersion(name='a', old_version='0.1.0', new_version='0.2.0', bump='minor'),
            PackageVersion(name='b', old_version='0.1.0', new_version='0.2.0', bump='minor'),
        ]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        assert not result.ok
        assert 'cycle_detection' in result.failed


class TestPreflightSkippedVersion:
    """Tests for skipped versions in conflict check."""

    @staticmethod
    def _make_packages(tmp_path: Path) -> list[Package]:
        pkg_dir = tmp_path / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(
                name='genkit',
                version='0.5.0',
                path=pkg_dir,
                manifest_path=pkg_dir / 'pyproject.toml',
            ),
        ]

    def test_skipped_version_not_checked(self, tmp_path: Path) -> None:
        """Skipped versions are not checked against the registry."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [
            PackageVersion(
                name='genkit',
                old_version='0.5.0',
                new_version='0.5.0',
                bump='',
                skipped=True,
            ),
        ]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(published={'genkit==0.5.0'}),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        # Should pass — skipped version is not checked.
        assert 'version_conflicts' in result.passed


class TestPreflightMetadataParseError:
    """Tests for metadata validation parse error path."""

    def test_unparseable_pyproject_warns(self, tmp_path: Path) -> None:
        """Unparseable pyproject.toml in metadata check produces a warning."""
        pkg_dir = tmp_path / 'packages' / 'broken'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text('this is not valid toml {{{{')

        packages = [
            Package(
                name='broken',
                version='0.1.0',
                path=pkg_dir,
                manifest_path=pyproject,
                is_publishable=True,
            ),
        ]
        graph = build_graph(packages)
        versions = [
            PackageVersion(name='broken', old_version='0.1.0', new_version='0.2.0', bump='minor'),
        ]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                ecosystem='python',
            ),
        )

        assert 'metadata_validation' in result.warnings
