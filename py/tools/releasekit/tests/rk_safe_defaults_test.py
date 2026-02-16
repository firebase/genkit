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

"""Tests for safe-by-default security behaviour.

Covers:
- Config defaults (provenance, signing, retries all on by default)
- Preflight: OIDC fail-closed in CI, source integrity, build-as-code, SLSA level
- Publisher: provenance/signing defaults
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest import mock

from releasekit.config import WorkspaceConfig
from releasekit.graph import build_graph
from releasekit.preflight import (
    PreflightResult,
    _check_build_as_code,
    _check_slsa_level,
    _check_source_integrity,
    _check_trusted_publisher,
    run_preflight,
)
from releasekit.publisher import PublishConfig
from releasekit.versions import PackageVersion
from releasekit.workspace import Package
from tests._fakes import FakePM as FakePackageManager, FakeRegistry, FakeVCS

# ── Helpers ──


def _github_ci_env(*, oidc: bool = True) -> dict[str, str]:
    """Return a dict simulating GitHub Actions CI environment."""
    env: dict[str, str] = {
        'CI': 'true',
        'GITHUB_ACTIONS': 'true',
        'GITHUB_SERVER_URL': 'https://github.com',
        'GITHUB_REPOSITORY': 'firebase/genkit',
        'GITHUB_SHA': 'abc123def456',
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ID': '12345',
        'GITHUB_WORKFLOW_REF': 'firebase/genkit/.github/workflows/release.yml@refs/heads/main',
        'RUNNER_ENVIRONMENT': 'github-hosted',
        'RUNNER_OS': 'Linux',
        'RUNNER_ARCH': 'X64',
    }
    if oidc:
        env['ACTIONS_ID_TOKEN_REQUEST_URL'] = 'https://token.actions.githubusercontent.com'
    return env


def _local_env() -> dict[str, str]:
    """Return a dict simulating a local (non-CI) environment."""
    return {
        'HOME': '/Users/dev',
        'USER': 'dev',
    }


def _make_packages(tmp_path: Path) -> list[Package]:
    pkg_dir = tmp_path / 'packages' / 'genkit'
    pkg_dir.mkdir(parents=True, exist_ok=True)
    return [
        Package(name='genkit', version='0.5.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml'),
    ]


# ── Config defaults ──


class TestConfigDefaults:
    """Verify that config defaults are safe-by-default."""

    def test_workspace_config_provenance_on(self) -> None:
        ws = WorkspaceConfig()
        assert ws.provenance is True

    def test_workspace_config_slsa_provenance_on(self) -> None:
        ws = WorkspaceConfig()
        assert ws.slsa_provenance is True

    def test_workspace_config_sign_provenance_on(self) -> None:
        ws = WorkspaceConfig()
        assert ws.sign_provenance is True

    def test_publish_config_provenance_on(self) -> None:
        pc = PublishConfig()
        assert pc.provenance is True

    def test_publish_config_slsa_provenance_on(self) -> None:
        pc = PublishConfig()
        assert pc.slsa_provenance is True

    def test_publish_config_sign_provenance_on(self) -> None:
        pc = PublishConfig()
        assert pc.sign_provenance is True

    def test_workspace_config_oci_cosign_sign_on(self) -> None:
        ws = WorkspaceConfig()
        assert ws.oci_cosign_sign is True

    def test_workspace_config_oci_sbom_attest_on(self) -> None:
        ws = WorkspaceConfig()
        assert ws.oci_sbom_attest is True

    def test_workspace_config_oci_push_target_empty(self) -> None:
        ws = WorkspaceConfig()
        assert ws.oci_push_target == ''

    def test_workspace_config_oci_repository_empty(self) -> None:
        ws = WorkspaceConfig()
        assert ws.oci_repository == ''

    def test_workspace_config_oci_remote_tags_empty(self) -> None:
        ws = WorkspaceConfig()
        assert ws.oci_remote_tags == []

    def test_publish_config_retries_nonzero(self) -> None:
        pc = PublishConfig()
        assert pc.max_retries >= 1

    def test_publish_config_verify_checksums_on(self) -> None:
        pc = PublishConfig()
        assert pc.verify_checksums is True

    def test_publish_config_smoke_test_on(self) -> None:
        pc = PublishConfig()
        assert pc.smoke_test is True


# ── _check_trusted_publisher ──


class TestTrustedPublisherCheck:
    """Tests for OIDC trusted publisher preflight check."""

    def test_ci_without_oidc_fails(self) -> None:
        """In CI, missing OIDC is a failure (fail-closed)."""
        env = _github_ci_env(oidc=False)
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_trusted_publisher(None, result)
        assert 'trusted_publisher' in result.failed
        assert 'OIDC' in result.errors['trusted_publisher']

    def test_ci_with_oidc_passes(self) -> None:
        """In CI with OIDC, check passes."""
        env = _github_ci_env(oidc=True)
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_trusted_publisher(None, result)
        assert 'trusted_publisher' in result.passed

    def test_local_without_oidc_passes(self) -> None:
        """Locally (no CI), OIDC is not required — check passes."""
        result = PreflightResult()
        with mock.patch.dict(os.environ, _local_env(), clear=True):
            _check_trusted_publisher(None, result)
        assert 'trusted_publisher' in result.passed
        assert result.ok

    def test_failure_hint_mentions_id_token_write(self) -> None:
        """Failure hint should mention the fix."""
        env = _github_ci_env(oidc=False)
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_trusted_publisher(None, result)
        hint = result.hints.get('trusted_publisher', '')
        assert 'id-token: write' in hint


# ── _check_source_integrity ──


class TestSourceIntegrityCheck:
    """Tests for source integrity metadata preflight check."""

    def test_ci_with_full_metadata_passes(self) -> None:
        env = _github_ci_env()
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_source_integrity(result)
        assert 'source_integrity' in result.passed

    def test_ci_missing_sha_fails(self) -> None:
        env = _github_ci_env()
        del env['GITHUB_SHA']
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_source_integrity(result)
        assert 'source_integrity' in result.failed
        assert 'commit SHA' in result.errors['source_integrity']

    def test_ci_missing_ref_fails(self) -> None:
        env = _github_ci_env()
        del env['GITHUB_REF']
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_source_integrity(result)
        assert 'source_integrity' in result.failed
        assert 'source ref' in result.errors['source_integrity']

    def test_ci_missing_repo_fails(self) -> None:
        env = _github_ci_env()
        del env['GITHUB_REPOSITORY']
        del env['GITHUB_SERVER_URL']
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_source_integrity(result)
        assert 'source_integrity' in result.failed
        assert 'repository' in result.errors['source_integrity']

    def test_local_missing_metadata_warns(self) -> None:
        """Locally, missing source metadata is a warning."""
        result = PreflightResult()
        with mock.patch.dict(os.environ, _local_env(), clear=True):
            _check_source_integrity(result)
        assert 'source_integrity' in result.warnings
        assert result.ok  # Warning, not failure.


# ── _check_build_as_code ──


class TestBuildAsCodeCheck:
    """Tests for build-as-code preflight check."""

    def test_ci_with_entry_point_passes(self) -> None:
        env = _github_ci_env()
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_build_as_code(result)
        assert 'build_as_code' in result.passed

    def test_ci_without_entry_point_warns(self) -> None:
        env = _github_ci_env()
        del env['GITHUB_WORKFLOW_REF']
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_build_as_code(result)
        assert 'build_as_code' in result.warnings

    def test_local_always_passes(self) -> None:
        """Local builds skip this check."""
        result = PreflightResult()
        with mock.patch.dict(os.environ, _local_env(), clear=True):
            _check_build_as_code(result)
        assert 'build_as_code' in result.passed


# ── _check_slsa_level ──


class TestSLSALevelCheck:
    """Tests for SLSA build level preflight check."""

    def test_local_warns_l1(self) -> None:
        result = PreflightResult()
        with mock.patch.dict(os.environ, _local_env(), clear=True):
            _check_slsa_level(result)
        assert 'slsa_build_level' in result.warnings
        assert 'L1' in result.warning_messages['slsa_build_level']

    def test_ci_l3_passes(self) -> None:
        env = _github_ci_env(oidc=True)
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_slsa_level(result)
        assert 'slsa_build_level' in result.passed

    def test_ci_self_hosted_warns_l2(self) -> None:
        env = _github_ci_env(oidc=True)
        env['RUNNER_ENVIRONMENT'] = 'self-hosted'
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_slsa_level(result)
        assert 'slsa_build_level' in result.warnings
        assert 'L2' in result.warning_messages['slsa_build_level']

    def test_ci_no_oidc_warns_l1(self) -> None:
        env = _github_ci_env(oidc=False)
        result = PreflightResult()
        with mock.patch.dict(os.environ, env, clear=True):
            _check_slsa_level(result)
        assert 'slsa_build_level' in result.warnings
        assert 'not be signed' in result.warning_messages['slsa_build_level']


# ── Full preflight integration ──


class TestPreflightIntegration:
    """Integration tests for run_preflight with new security checks."""

    def test_full_github_ci_with_oidc_passes(self, tmp_path: Path) -> None:
        """Full CI environment with OIDC passes all security checks."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        env = _github_ci_env(oidc=True)
        with mock.patch.dict(os.environ, env, clear=True):
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

        # Should pass all security checks.
        assert 'trusted_publisher' in result.passed
        assert 'source_integrity' in result.passed
        assert 'build_as_code' in result.passed
        assert 'slsa_build_level' in result.passed

    def test_local_build_warns_but_passes(self, tmp_path: Path) -> None:
        """Local build warns about security but doesn't block."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        with mock.patch.dict(os.environ, _local_env(), clear=True):
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

        # Local builds should warn on some checks but not fail.
        assert result.ok
        # trusted_publisher passes locally (OIDC not required).
        assert 'trusted_publisher' in result.passed
        # source_integrity and slsa_build_level warn locally.
        assert 'source_integrity' in result.warnings
        assert 'slsa_build_level' in result.warnings

    def test_ci_without_oidc_blocks_publish(self, tmp_path: Path) -> None:
        """CI without OIDC blocks publishing (fail-closed)."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        env = _github_ci_env(oidc=False)
        with mock.patch.dict(os.environ, env, clear=True):
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
        assert 'trusted_publisher' in result.failed

    def test_new_checks_present_in_results(self, tmp_path: Path) -> None:
        """All new security checks appear in results."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        env = _github_ci_env(oidc=True)
        with mock.patch.dict(os.environ, env, clear=True):
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

        all_checks = result.passed + result.warnings + result.failed
        assert 'trusted_publisher' in all_checks
        assert 'source_integrity' in all_checks
        assert 'build_as_code' in all_checks
        assert 'slsa_build_level' in all_checks
