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

"""Tests for OpenSSF Scorecard-aligned security checks.

Validates the local Scorecard checks in :mod:`releasekit.scorecard`.

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ What We Test                                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ File existence      │ SECURITY.md, dependabot.yml, CI workflows    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Pinned deps         │ GitHub Actions pinned by SHA vs tag           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Token permissions   │ Overly permissive write-all detection         │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    test → create temp repo structure → run_scorecard_checks() → assert results
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.scorecard import (
    ScorecardCheckResult,
    run_scorecard_checks,
)


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Create a minimal repo structure for testing."""
    return tmp_path


class TestSecurityMd:
    """Tests for SECURITY.md check."""

    def test_security_md_at_root(self, repo_root: Path) -> None:
        """SECURITY.md at repo root passes."""
        (repo_root / 'SECURITY.md').write_text('# Security Policy\n')
        results = run_scorecard_checks(repo_root)
        security = next(r for r in results if r.check == 'security_md')
        assert security.passed

    def test_security_md_in_github(self, repo_root: Path) -> None:
        """SECURITY.md in .github/ passes."""
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'SECURITY.md').write_text('# Security\n')
        results = run_scorecard_checks(repo_root)
        security = next(r for r in results if r.check == 'security_md')
        assert security.passed

    def test_security_md_in_docs(self, repo_root: Path) -> None:
        """SECURITY.md in docs/ passes."""
        (repo_root / 'docs').mkdir()
        (repo_root / 'docs' / 'SECURITY.md').write_text('# Security\n')
        results = run_scorecard_checks(repo_root)
        security = next(r for r in results if r.check == 'security_md')
        assert security.passed

    def test_no_security_md(self, repo_root: Path) -> None:
        """Missing SECURITY.md fails."""
        results = run_scorecard_checks(repo_root)
        security = next(r for r in results if r.check == 'security_md')
        assert not security.passed
        assert security.hint


class TestDependencyUpdateTool:
    """Tests for dependency update tool check."""

    def test_dependabot_yml(self, repo_root: Path) -> None:
        """dependabot.yml passes."""
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yml').write_text('version: 2\n')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed

    def test_renovate_json(self, repo_root: Path) -> None:
        """renovate.json passes."""
        (repo_root / 'renovate.json').write_text('{}')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed

    def test_renovaterc(self, repo_root: Path) -> None:
        """.renovaterc passes."""
        (repo_root / '.renovaterc').write_text('{}')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed

    def test_no_dep_tool(self, repo_root: Path) -> None:
        """Missing dependency update tool fails."""
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert not dep.passed


class TestCITests:
    """Tests for CI workflow check."""

    def test_github_actions(self, repo_root: Path) -> None:
        """GitHub Actions workflows pass."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text('name: CI\n')
        results = run_scorecard_checks(repo_root)
        ci = next(r for r in results if r.check == 'ci_tests')
        assert ci.passed

    def test_gitlab_ci(self, repo_root: Path) -> None:
        """GitLab CI config passes."""
        (repo_root / '.gitlab-ci.yml').write_text('stages:\n  - test\n')
        results = run_scorecard_checks(repo_root)
        ci = next(r for r in results if r.check == 'ci_tests')
        assert ci.passed

    def test_circleci(self, repo_root: Path) -> None:
        """CircleCI config passes."""
        circleci_dir = repo_root / '.circleci'
        circleci_dir.mkdir()
        (circleci_dir / 'config.yml').write_text('version: 2.1\n')
        results = run_scorecard_checks(repo_root)
        ci = next(r for r in results if r.check == 'ci_tests')
        assert ci.passed

    def test_no_ci(self, repo_root: Path) -> None:
        """Missing CI config fails."""
        results = run_scorecard_checks(repo_root)
        ci = next(r for r in results if r.check == 'ci_tests')
        assert not ci.passed


class TestPinnedDependencies:
    """Tests for GitHub Actions pinning check."""

    def test_pinned_by_sha(self, repo_root: Path) -> None:
        """Actions pinned by SHA pass."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text(
            'jobs:\n  build:\n    steps:\n      - uses: actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29\n'
        )
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert pinned.passed

    def test_unpinned_by_tag(self, repo_root: Path) -> None:
        """Actions pinned by tag fail."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text('jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n')
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert not pinned.passed

    def test_no_workflows(self, repo_root: Path) -> None:
        """No workflows directory passes (nothing to check)."""
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert pinned.passed


class TestTokenPermissions:
    """Tests for token permissions check."""

    def test_least_privilege(self, repo_root: Path) -> None:
        """Workflows with specific permissions pass."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text('permissions:\n  contents: read\n  id-token: write\n')
        results = run_scorecard_checks(repo_root)
        perms = next(r for r in results if r.check == 'token_permissions')
        assert perms.passed

    def test_write_all(self, repo_root: Path) -> None:
        """Workflows with write-all fail."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text('permissions: write-all\n')
        results = run_scorecard_checks(repo_root)
        perms = next(r for r in results if r.check == 'token_permissions')
        assert not perms.passed


class TestSignedReleases:
    """Tests for signed releases check."""

    def test_sigstore_bundles_exist(self, repo_root: Path) -> None:
        """Sigstore bundles in dist/ pass."""
        dist = repo_root / 'dist'
        dist.mkdir()
        (dist / 'pkg-1.0.tar.gz.sigstore.json').write_text('{}')
        results = run_scorecard_checks(repo_root)
        signed = next(r for r in results if r.check == 'signed_releases')
        assert signed.passed

    def test_no_artifacts(self, repo_root: Path) -> None:
        """No artifact directories passes (first release)."""
        results = run_scorecard_checks(repo_root)
        signed = next(r for r in results if r.check == 'signed_releases')
        assert signed.passed


class TestPinnedDependenciesEdgeCases:
    """Additional edge-case tests for pinned dependencies check."""

    def test_comment_lines_ignored(self, repo_root: Path) -> None:
        """Comment lines with uses: patterns are ignored."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text(
            'jobs:\n'
            '  build:\n'
            '    steps:\n'
            '      # - uses: actions/checkout@v4\n'
            '      - uses: actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29\n'
        )
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert pinned.passed

    def test_yaml_extension_variant(self, repo_root: Path) -> None:
        """Workflows with .yaml extension are also checked."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yaml').write_text('jobs:\n  build:\n    steps:\n      - uses: actions/checkout@v4\n')
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert not pinned.passed

    def test_unreadable_workflow_skipped(self, repo_root: Path) -> None:
        """Unreadable workflow files are skipped without crashing."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        # Create a directory with .yml extension (will fail read_text).
        (wf_dir / 'bad.yml').mkdir()
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert pinned.passed  # No readable workflows = pass.

    def test_mixed_pinned_and_unpinned(self, repo_root: Path) -> None:
        """Mix of pinned and unpinned actions reports unpinned count."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'ci.yml').write_text(
            'jobs:\n'
            '  build:\n'
            '    steps:\n'
            '      - uses: actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29\n'
            '      - uses: actions/setup-python@v5\n'
            '      - uses: actions/cache@v3\n'
        )
        results = run_scorecard_checks(repo_root)
        pinned = next(r for r in results if r.check == 'pinned_dependencies')
        assert not pinned.passed
        assert '2 action(s)' in pinned.message


class TestTokenPermissionsEdgeCases:
    """Additional edge-case tests for token permissions check."""

    def test_unreadable_workflow_skipped(self, repo_root: Path) -> None:
        """Unreadable workflow files are skipped without crashing."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        # Create a directory with .yml extension (will fail read_text).
        (wf_dir / 'bad.yml').mkdir()
        results = run_scorecard_checks(repo_root)
        perms = next(r for r in results if r.check == 'token_permissions')
        assert perms.passed

    def test_multiple_workflows_one_bad(self, repo_root: Path) -> None:
        """One bad workflow among many is flagged."""
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir(parents=True)
        (wf_dir / 'good.yml').write_text('permissions:\n  contents: read\n')
        (wf_dir / 'bad.yml').write_text('permissions: write-all\n')
        results = run_scorecard_checks(repo_root)
        perms = next(r for r in results if r.check == 'token_permissions')
        assert not perms.passed
        assert 'bad.yml' in perms.message


class TestDependencyUpdateToolEdgeCases:
    """Additional edge-case tests for dependency update tool check."""

    def test_dependabot_yaml(self, repo_root: Path) -> None:
        """dependabot.yaml (not .yml) passes."""
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yaml').write_text('version: 2\n')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed

    def test_renovate_json5(self, repo_root: Path) -> None:
        """renovate.json5 passes."""
        (repo_root / 'renovate.json5').write_text('{}')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed

    def test_renovaterc_json(self, repo_root: Path) -> None:
        """.renovaterc.json passes."""
        (repo_root / '.renovaterc.json').write_text('{}')
        results = run_scorecard_checks(repo_root)
        dep = next(r for r in results if r.check == 'dependency_update_tool')
        assert dep.passed


class TestSignedReleasesEdgeCases:
    """Additional edge-case tests for signed releases check."""

    def test_artifacts_dir(self, repo_root: Path) -> None:
        """Sigstore bundles in artifacts/ pass."""
        artifacts = repo_root / 'artifacts'
        artifacts.mkdir()
        (artifacts / 'pkg-1.0.tar.gz.sigstore.json').write_text('{}')
        results = run_scorecard_checks(repo_root)
        signed = next(r for r in results if r.check == 'signed_releases')
        assert signed.passed

    def test_empty_dist_dir(self, repo_root: Path) -> None:
        """Empty dist/ directory with no bundles still passes (first release)."""
        (repo_root / 'dist').mkdir()
        results = run_scorecard_checks(repo_root)
        signed = next(r for r in results if r.check == 'signed_releases')
        assert signed.passed


class TestScorecardCheckResult:
    """Tests for the ScorecardCheckResult dataclass."""

    def test_default_severity(self) -> None:
        """Default severity is 'warning'."""
        r = ScorecardCheckResult(check='test', passed=True)
        assert r.severity == 'warning'

    def test_failed_result_has_hint(self) -> None:
        """Failed results should have hints."""
        r = ScorecardCheckResult(
            check='test',
            passed=False,
            message='Something failed',
            hint='Fix it',
        )
        assert r.hint == 'Fix it'
        assert not r.passed


class TestRunScorecardChecks:
    """Integration tests for the full scorecard suite."""

    def test_returns_all_checks(self, repo_root: Path) -> None:
        """All 6 checks are returned."""
        results = run_scorecard_checks(repo_root)
        assert len(results) == 6

    def test_all_checks_have_names(self, repo_root: Path) -> None:
        """Every result has a non-empty check name."""
        results = run_scorecard_checks(repo_root)
        for r in results:
            assert r.check

    def test_check_names_are_unique(self, repo_root: Path) -> None:
        """All check names are unique."""
        results = run_scorecard_checks(repo_root)
        names = [r.check for r in results]
        assert len(names) == len(set(names))

    def test_well_configured_repo(self, repo_root: Path) -> None:
        """A well-configured repo passes all checks."""
        (repo_root / 'SECURITY.md').write_text('# Security\n')
        (repo_root / '.github').mkdir()
        (repo_root / '.github' / 'dependabot.yml').write_text('version: 2\n')
        wf_dir = repo_root / '.github' / 'workflows'
        wf_dir.mkdir()
        (wf_dir / 'ci.yml').write_text(
            'permissions:\n  contents: read\n'
            'jobs:\n  build:\n    steps:\n'
            '      - uses: actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29\n'
        )
        results = run_scorecard_checks(repo_root)
        assert all(r.passed for r in results)

    def test_empty_repo_has_failures(self, repo_root: Path) -> None:
        """Empty repo fails security_md, dependency_update_tool, ci_tests."""
        results = run_scorecard_checks(repo_root)
        failed = [r for r in results if not r.passed]
        failed_names = {r.check for r in failed}
        assert 'security_md' in failed_names
        assert 'dependency_update_tool' in failed_names
        assert 'ci_tests' in failed_names
