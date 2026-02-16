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

"""Tests for releasekit.versioning (Conventional Commits + bump computation)."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.graph import build_graph
from releasekit.versioning import (
    BumpType,
    _apply_bump,
    _max_bump,
    compute_bumps,
    parse_conventional_commit,
)
from releasekit.workspace import Package
from tests._fakes import FakeVCS


class TestParseConventionalCommit:
    """Tests for parse_conventional_commit."""

    def test_feat(self) -> None:
        """A 'feat:' commit produces a MINOR bump."""
        cc = parse_conventional_commit('feat: add streaming support')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.bump == BumpType.MINOR
        assert cc.description == 'add streaming support'
        assert cc.breaking is False

    def test_fix(self) -> None:
        """A 'fix:' commit produces a PATCH bump."""
        cc = parse_conventional_commit('fix: resolve null pointer')
        assert cc is not None
        assert cc.type == 'fix'
        assert cc.bump == BumpType.PATCH

    def test_perf(self) -> None:
        """A 'perf:' commit produces a PATCH bump."""
        cc = parse_conventional_commit('perf: optimize hot loop')
        assert cc is not None
        assert cc.type == 'perf'
        assert cc.bump == BumpType.PATCH

    def test_chore(self) -> None:
        """A 'chore:' commit produces no bump."""
        cc = parse_conventional_commit('chore: update deps')
        assert cc is not None
        assert cc.type == 'chore'
        assert cc.bump == BumpType.NONE

    def test_docs(self) -> None:
        """A 'docs:' commit produces no bump."""
        cc = parse_conventional_commit('docs: update README')
        assert cc is not None
        assert cc.bump == BumpType.NONE

    def test_ci(self) -> None:
        """A 'ci:' commit produces no bump."""
        cc = parse_conventional_commit('ci: add coverage')
        assert cc is not None
        assert cc.bump == BumpType.NONE

    def test_scope(self) -> None:
        """Scoped commits are parsed correctly."""
        cc = parse_conventional_commit('feat(auth): add OAuth2')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.scope == 'auth'
        assert cc.bump == BumpType.MINOR

    def test_breaking_bang(self) -> None:
        """The '!' indicator marks a breaking change (MAJOR)."""
        cc = parse_conventional_commit('fix!: remove deprecated API')
        assert cc is not None
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_breaking_scope_bang(self) -> None:
        """Breaking change with scope."""
        cc = parse_conventional_commit('feat(api)!: redesign endpoints')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.scope == 'api'
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_breaking_change_footer(self) -> None:
        """BREAKING CHANGE footer triggers MAJOR (spec rule 12)."""
        cc = parse_conventional_commit('feat: new API\n\nBREAKING CHANGE: old API removed')
        assert cc is not None
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_non_conventional(self) -> None:
        """Non-conventional messages return None."""
        assert parse_conventional_commit('Update README.md') is None
        assert parse_conventional_commit('Merge pull request #42') is None
        assert parse_conventional_commit('WIP') is None

    def test_sha_preserved(self) -> None:
        """The SHA is stored on the result."""
        cc = parse_conventional_commit('fix: bug', sha='abc123')
        assert cc is not None
        assert cc.sha == 'abc123'

    def test_empty_description(self) -> None:
        """Commit with no description after colon returns None."""
        assert parse_conventional_commit('feat:') is None
        assert parse_conventional_commit('feat: ') is None


class TestMaxBump:
    """Tests for _max_bump."""

    def test_major_wins(self) -> None:
        """MAJOR always wins."""
        assert _max_bump(BumpType.MAJOR, BumpType.MINOR) == BumpType.MAJOR
        assert _max_bump(BumpType.MINOR, BumpType.MAJOR) == BumpType.MAJOR

    def test_minor_over_patch(self) -> None:
        """MINOR beats PATCH."""
        assert _max_bump(BumpType.MINOR, BumpType.PATCH) == BumpType.MINOR

    def test_patch_over_none(self) -> None:
        """PATCH beats NONE."""
        assert _max_bump(BumpType.PATCH, BumpType.NONE) == BumpType.PATCH

    def test_same(self) -> None:
        """Same bump type returns itself."""
        assert _max_bump(BumpType.MINOR, BumpType.MINOR) == BumpType.MINOR


class TestApplyBump:
    """Tests for _apply_bump."""

    def test_major(self) -> None:
        """Major bump increments major, resets minor and patch."""
        assert _apply_bump('1.2.3', BumpType.MAJOR) == '2.0.0'

    def test_minor(self) -> None:
        """Minor bump increments minor, resets patch."""
        assert _apply_bump('1.2.3', BumpType.MINOR) == '1.3.0'

    def test_patch(self) -> None:
        """Patch bump increments patch."""
        assert _apply_bump('1.2.3', BumpType.PATCH) == '1.2.4'

    def test_none(self) -> None:
        """No bump returns same version."""
        assert _apply_bump('1.2.3', BumpType.NONE) == '1.2.3'

    def test_prerelease_patch(self) -> None:
        """Patch bump with prerelease label adds semver suffix."""
        assert _apply_bump('1.2.3', BumpType.PATCH, 'rc') == '1.2.4-rc.1'

    def test_prerelease_minor(self) -> None:
        """Minor bump with prerelease label applies to bumped minor."""
        assert _apply_bump('1.2.3', BumpType.MINOR, 'rc') == '1.3.0-rc.1'

    def test_prerelease_major(self) -> None:
        """Major bump with prerelease label applies to bumped major."""
        assert _apply_bump('1.2.3', BumpType.MAJOR, 'rc') == '2.0.0-rc.1'

    def test_prerelease_pep440(self) -> None:
        """Prerelease with pep440 scheme uses PEP 440 suffixes on bumped version."""
        assert _apply_bump('1.2.3', BumpType.PATCH, 'rc', 'pep440') == '1.2.4rc1'
        assert _apply_bump('1.2.3', BumpType.PATCH, 'alpha', 'pep440') == '1.2.4a1'
        assert _apply_bump('1.2.3', BumpType.PATCH, 'beta', 'pep440') == '1.2.4b1'
        assert _apply_bump('1.2.3', BumpType.PATCH, 'dev', 'pep440') == '1.2.4.dev1'

    def test_prerelease_pep440_minor(self) -> None:
        """PEP 440 prerelease on minor bump applies to bumped minor."""
        assert _apply_bump('1.2.3', BumpType.MINOR, 'rc', 'pep440') == '1.3.0rc1'
        assert _apply_bump('0.5.0', BumpType.MINOR, 'beta', 'pep440') == '0.6.0b1'

    def test_prerelease_pep440_major(self) -> None:
        """PEP 440 prerelease on major bump applies to bumped major."""
        assert _apply_bump('1.2.3', BumpType.MAJOR, 'alpha', 'pep440') == '2.0.0a1'

    def test_prerelease_semver_labels(self) -> None:
        """Prerelease with semver scheme uses dash-dot format."""
        assert _apply_bump('1.2.3', BumpType.PATCH, 'alpha', 'semver') == '1.2.4-alpha.1'
        assert _apply_bump('1.2.3', BumpType.PATCH, 'beta', 'semver') == '1.2.4-beta.1'
        assert _apply_bump('1.2.3', BumpType.PATCH, 'dev', 'semver') == '1.2.4-dev.1'

    def test_no_prerelease_label_means_stable(self) -> None:
        """Empty prerelease label produces a stable version."""
        assert _apply_bump('1.2.3', BumpType.PATCH) == '1.2.4'
        assert _apply_bump('1.2.3', BumpType.MINOR) == '1.3.0'

    def test_zero_major(self) -> None:
        """Bumping from 0.x.y works correctly."""
        assert _apply_bump('0.4.0', BumpType.MINOR) == '0.5.0'
        assert _apply_bump('0.4.0', BumpType.MAJOR) == '1.0.0'

    def test_invalid_version_too_few_parts(self) -> None:
        """Raises ReleaseKitError for versions with fewer than 3 parts."""
        with pytest.raises(ReleaseKitError):
            _apply_bump('1.0', BumpType.PATCH)

    def test_invalid_version_non_numeric(self) -> None:
        """Raises ReleaseKitError for non-numeric version parts."""
        with pytest.raises(ReleaseKitError):
            _apply_bump('a.b.c', BumpType.PATCH)

    def test_strips_prerelease_metadata(self) -> None:
        """Existing prerelease metadata is stripped before bumping."""
        assert _apply_bump('1.2.3-rc1', BumpType.PATCH) == '1.2.4'
        assert _apply_bump('1.2.3+build42', BumpType.MINOR) == '1.3.0'

    def test_strips_pep440_prerelease(self) -> None:
        """PEP 440 pre-release suffixes are stripped before bumping."""
        assert _apply_bump('1.2.3rc1', BumpType.PATCH) == '1.2.4'
        assert _apply_bump('1.2.3a2', BumpType.MINOR) == '1.3.0'
        assert _apply_bump('1.2.3b1', BumpType.MAJOR) == '2.0.0'
        assert _apply_bump('1.2.3.dev5', BumpType.PATCH) == '1.2.4'


class TestComputeBumps:
    """Integration tests for compute_bumps with FakeVCS."""

    def _make_pkg(self, name: str, version: str, path: str) -> Package:
        """Helper to create a Package for testing."""
        return Package(
            name=name,
            version=version,
            path=Path(path),
            manifest_path=Path(path) / 'pyproject.toml',
        )

    @pytest.mark.asyncio
    async def test_scopes_commits_per_package(self) -> None:
        """Only commits touching a package's path bump that package."""
        vcs = FakeVCS(
            log_by_path={
                '/workspace/packages/genkit': [
                    'aaa feat: add streaming',
                ],
                '/workspace/plugins/google-genai': [
                    'bbb fix: resolve timeout',
                ],
            },
        )
        packages = [
            self._make_pkg('genkit', '0.4.0', '/workspace/packages/genkit'),
            self._make_pkg('genkit-plugin-google-genai', '0.4.0', '/workspace/plugins/google-genai'),
        ]

        results = await compute_bumps(packages, vcs)

        assert len(results) == 2
        # genkit gets a feat → minor bump
        assert results[0].name == 'genkit'
        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.5.0'
        assert results[0].skipped is False
        # google-genai gets a fix → patch bump
        assert results[1].name == 'genkit-plugin-google-genai'
        assert results[1].bump == 'patch'
        assert results[1].new_version == '0.4.1'

    @pytest.mark.asyncio
    async def test_no_commits_skips_package(self) -> None:
        """Packages with no commits are skipped."""
        vcs = FakeVCS(
            log_by_path={
                '/workspace/packages/genkit': [
                    'aaa feat: add feature',
                ],
            },
        )
        packages = [
            self._make_pkg('genkit', '0.4.0', '/workspace/packages/genkit'),
            self._make_pkg('genkit-plugin-foo', '0.4.0', '/workspace/plugins/foo'),
        ]

        results = await compute_bumps(packages, vcs)

        assert results[0].skipped is False
        assert results[1].skipped is True
        assert results[1].new_version == '0.4.0'

    @pytest.mark.asyncio
    async def test_force_unchanged(self) -> None:
        """force_unchanged bumps skipped packages to patch."""
        vcs = FakeVCS(log_by_path={})
        packages = [
            self._make_pkg('genkit', '1.0.0', '/workspace/packages/genkit'),
        ]

        results = await compute_bumps(packages, vcs, force_unchanged=True)

        assert results[0].skipped is False
        assert results[0].bump == 'patch'
        assert results[0].new_version == '1.0.1'

    @pytest.mark.asyncio
    async def test_prerelease_mode(self) -> None:
        """Prerelease mode applies suffix to the correctly bumped version."""
        vcs = FakeVCS(
            log_by_path={
                '/workspace/packages/genkit': [
                    'aaa feat: add feature',
                ],
            },
        )
        packages = [
            self._make_pkg('genkit', '0.4.0', '/workspace/packages/genkit'),
        ]

        results = await compute_bumps(packages, vcs, prerelease='rc')

        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.5.0-rc.1'

    @pytest.mark.asyncio
    async def test_breaking_change_major_bump(self) -> None:
        """Breaking changes result in major version bumps."""
        vcs = FakeVCS(
            log_by_path={
                '/workspace/packages/genkit': [
                    'aaa feat!: redesign API',
                ],
            },
        )
        packages = [
            self._make_pkg('genkit', '1.2.3', '/workspace/packages/genkit'),
        ]

        results = await compute_bumps(packages, vcs)

        assert results[0].bump == 'major'
        assert results[0].new_version == '2.0.0'

    @pytest.mark.asyncio
    async def test_strongest_bump_wins(self) -> None:
        """When multiple commits affect a package, the strongest bump wins."""
        vcs = FakeVCS(
            log_by_path={
                '/workspace/packages/genkit': [
                    'aaa fix: small fix',
                    'bbb feat: new feature',
                    'ccc chore: update deps',
                ],
            },
        )
        packages = [
            self._make_pkg('genkit', '1.0.0', '/workspace/packages/genkit'),
        ]

        results = await compute_bumps(packages, vcs)

        # feat (minor) > fix (patch) > chore (none)
        assert results[0].bump == 'minor'
        assert results[0].new_version == '1.1.0'


class TestTransitivePropagation:
    """Tests for transitive PATCH propagation via dependency graph."""

    def _make_pkg(
        self,
        name: str,
        version: str,
        path: str,
        internal_deps: list[str] | None = None,
    ) -> Package:
        """Helper to create a Package with optional internal deps."""
        return Package(
            name=name,
            version=version,
            path=Path(path),
            manifest_path=Path(path) / 'pyproject.toml',
            internal_deps=internal_deps or [],
        )

    @pytest.mark.asyncio
    async def test_direct_dependent_gets_patch(self) -> None:
        """A bumped package causes its direct dependent to get a PATCH bump."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
        ]
        graph = build_graph(packages)

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        results = await compute_bumps(packages, vcs, graph=graph)

        # genkit gets a direct minor bump.
        assert results[0].name == 'genkit'
        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.6.0'
        # foo gets a transitive PATCH bump.
        assert results[1].name == 'genkit-plugin-foo'
        assert results[1].bump == 'patch'
        assert results[1].new_version == '0.5.1'
        assert 'dependency genkit bumped' in results[1].reason

    @pytest.mark.asyncio
    async def test_multi_level_propagation(self) -> None:
        """Propagation reaches transitive dependents (A → B → C)."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
            self._make_pkg(
                'sample-app',
                '0.1.0',
                '/ws/samples/app',
                internal_deps=['genkit-plugin-foo'],
            ),
        ]
        graph = build_graph(packages)

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        results = await compute_bumps(packages, vcs, graph=graph)

        assert results[0].bump == 'minor'  # genkit: direct
        assert results[1].bump == 'patch'  # foo: transitive from genkit
        assert results[2].bump == 'patch'  # sample: transitive from foo

    @pytest.mark.asyncio
    async def test_no_graph_skips_propagation(self) -> None:
        """Without a graph, dependents are not bumped transitively."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
        ]

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        # No graph passed — old behavior.
        results = await compute_bumps(packages, vcs)

        assert results[0].bump == 'minor'  # genkit: direct
        assert results[1].skipped is True  # foo: no commits, no propagation

    @pytest.mark.asyncio
    async def test_already_bumped_not_downgraded(self) -> None:
        """A package with a direct bump is not downgraded to PATCH."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
        ]
        graph = build_graph(packages)

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa fix: bugfix'],
                '/ws/plugins/foo': ['bbb feat: new feature'],
            },
        )

        results = await compute_bumps(packages, vcs, graph=graph)

        assert results[0].bump == 'patch'  # genkit: direct fix
        # foo has a direct minor bump — should NOT be downgraded to patch.
        assert results[1].bump == 'minor'
        assert results[1].new_version == '0.6.0'


class TestPropagateBumpsDisabled:
    """Tests for propagate_bumps=False (no transitive dependency bumps).

    When ``propagate_bumps`` is ``False`` in the workspace config, bumping
    a library should NOT trigger PATCH bumps in its dependents. Only
    packages with direct commits get bumped. This is useful when apps
    depend on libraries but should not be released just because the
    library changed.
    """

    def _make_pkg(
        self,
        name: str,
        version: str,
        path: str,
        internal_deps: list[str] | None = None,
    ) -> Package:
        """Helper to create a Package with optional internal deps."""
        return Package(
            name=name,
            version=version,
            path=Path(path),
            manifest_path=Path(path) / 'pyproject.toml',
            internal_deps=internal_deps or [],
        )

    @pytest.mark.asyncio
    async def test_dependent_not_bumped_when_propagation_disabled(self) -> None:
        """With propagation off, a dependent is NOT bumped when its dep changes."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
        ]

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        # No graph passed → simulates propagate_bumps=False.
        results = await compute_bumps(packages, vcs)

        assert results[0].name == 'genkit'
        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.6.0'
        # foo has no commits and no propagation → skipped.
        assert results[1].name == 'genkit-plugin-foo'
        assert results[1].skipped is True
        assert results[1].bump == 'none'

    @pytest.mark.asyncio
    async def test_multi_level_chain_not_propagated(self) -> None:
        """With propagation off, A→B→C chain does not cascade bumps."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
            self._make_pkg(
                'sample-app',
                '0.1.0',
                '/ws/samples/app',
                internal_deps=['genkit-plugin-foo'],
            ),
        ]

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        # No graph → no propagation.
        results = await compute_bumps(packages, vcs)

        assert results[0].bump == 'minor'  # genkit: direct
        assert results[1].skipped is True  # foo: no propagation
        assert results[2].skipped is True  # sample: no propagation

    @pytest.mark.asyncio
    async def test_direct_commits_still_bumped(self) -> None:
        """With propagation off, packages with their own commits still bump."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
            self._make_pkg(
                'sample-app',
                '0.1.0',
                '/ws/samples/app',
                internal_deps=['genkit-plugin-foo'],
            ),
        ]

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
                '/ws/samples/app': ['bbb fix: fix sample bug'],
            },
        )

        # No graph → no propagation.
        results = await compute_bumps(packages, vcs)

        assert results[0].bump == 'minor'  # genkit: direct feat
        assert results[1].skipped is True  # foo: no commits, no propagation
        assert results[2].bump == 'patch'  # sample: direct fix commit
        assert results[2].new_version == '0.1.1'

    @pytest.mark.asyncio
    async def test_contrast_with_propagation_enabled(self) -> None:
        """Same scenario with propagation ON bumps the dependent."""
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg(
                'genkit-plugin-foo',
                '0.5.0',
                '/ws/plugins/foo',
                internal_deps=['genkit'],
            ),
            self._make_pkg(
                'sample-app',
                '0.1.0',
                '/ws/samples/app',
                internal_deps=['genkit-plugin-foo'],
            ),
        ]
        graph = build_graph(packages)

        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )

        # With graph → propagation ON.
        results = await compute_bumps(packages, vcs, graph=graph)

        assert results[0].bump == 'minor'  # genkit: direct
        assert results[1].bump == 'patch'  # foo: transitive
        assert results[2].bump == 'patch'  # sample: transitive from foo


class TestSynchronizedMode:
    """Tests for synchronized (lockstep) versioning."""

    def _make_pkg(self, name: str, version: str, path: str) -> Package:
        """Helper to create a Package for testing."""
        return Package(
            name=name,
            version=version,
            path=Path(path),
            manifest_path=Path(path) / 'pyproject.toml',
        )

    @pytest.mark.asyncio
    async def test_all_get_max_bump(self) -> None:
        """In synchronized mode, all packages get the workspace-max bump."""
        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: new feature'],
                '/ws/plugins/foo': ['bbb fix: small fix'],
            },
        )
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg('genkit-plugin-foo', '0.5.0', '/ws/plugins/foo'),
            self._make_pkg('genkit-plugin-bar', '0.5.0', '/ws/plugins/bar'),
        ]

        results = await compute_bumps(packages, vcs, synchronize=True)

        # All packages get minor (the max across the workspace).
        for result in results:
            assert result.bump == 'minor'
            assert result.new_version == '0.6.0'
            assert result.skipped is False

    @pytest.mark.asyncio
    async def test_unchanged_get_reason(self) -> None:
        """Unchanged packages in synchronized mode get a 'synchronized:' reason."""
        vcs = FakeVCS(
            log_by_path={
                '/ws/packages/genkit': ['aaa feat: core update'],
            },
        )
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg('genkit-plugin-foo', '0.5.0', '/ws/plugins/foo'),
        ]

        results = await compute_bumps(packages, vcs, synchronize=True)

        # genkit has a direct reason.
        assert 'feat: core update' in results[0].reason
        # foo was unchanged but gets synchronized reason.
        assert 'synchronized:' in results[1].reason

    @pytest.mark.asyncio
    async def test_no_commits_anywhere(self) -> None:
        """If no packages have commits, synchronized mode skips all."""
        vcs = FakeVCS(log_by_path={})
        packages = [
            self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit'),
            self._make_pkg('genkit-plugin-foo', '0.5.0', '/ws/plugins/foo'),
        ]

        results = await compute_bumps(packages, vcs, synchronize=True)

        for result in results:
            assert result.skipped is True
            assert result.bump == 'none'


class TestMajorOnZero:
    """Tests for major_on_zero behavior in compute_bumps."""

    @staticmethod
    def _make_pkg(name: str, version: str, path: str) -> Package:
        p = Path(path)
        return Package(name=name, version=version, path=p, manifest_path=p / 'pyproject.toml')

    @pytest.mark.asyncio
    async def test_breaking_downgraded_to_minor_on_zero(self) -> None:
        """Breaking change on 0.x produces MINOR when major_on_zero=False."""
        vcs = FakeVCS(
            log_by_path={'/ws/packages/genkit': ['aaa feat!: breaking API change']},
        )
        packages = [self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit')]

        results = await compute_bumps(packages, vcs, major_on_zero=False)

        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.6.0'

    @pytest.mark.asyncio
    async def test_breaking_allowed_on_zero_when_enabled(self) -> None:
        """Breaking change on 0.x produces MAJOR when major_on_zero=True."""
        vcs = FakeVCS(
            log_by_path={'/ws/packages/genkit': ['aaa feat!: breaking API change']},
        )
        packages = [self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit')]

        results = await compute_bumps(packages, vcs, major_on_zero=True)

        assert results[0].bump == 'major'
        assert results[0].new_version == '1.0.0'

    @pytest.mark.asyncio
    async def test_breaking_on_1x_always_major(self) -> None:
        """Breaking change on 1.x always produces MAJOR regardless of flag."""
        vcs = FakeVCS(
            log_by_path={'/ws/packages/genkit': ['aaa feat!: breaking change']},
        )
        packages = [self._make_pkg('genkit', '1.2.0', '/ws/packages/genkit')]

        results = await compute_bumps(packages, vcs, major_on_zero=False)

        assert results[0].bump == 'major'
        assert results[0].new_version == '2.0.0'

    @pytest.mark.asyncio
    async def test_default_is_false(self) -> None:
        """Default major_on_zero=False prevents 0.x -> 1.0.0."""
        vcs = FakeVCS(
            log_by_path={'/ws/packages/genkit': ['aaa feat!: break everything']},
        )
        packages = [self._make_pkg('genkit', '0.9.0', '/ws/packages/genkit')]

        # No major_on_zero argument — should default to False.
        results = await compute_bumps(packages, vcs)

        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.10.0'

    @pytest.mark.asyncio
    async def test_non_breaking_unaffected(self) -> None:
        """Non-breaking commits are unaffected by major_on_zero."""
        vcs = FakeVCS(
            log_by_path={'/ws/packages/genkit': ['aaa feat: new feature']},
        )
        packages = [self._make_pkg('genkit', '0.5.0', '/ws/packages/genkit')]

        results = await compute_bumps(packages, vcs, major_on_zero=False)

        assert results[0].bump == 'minor'
        assert results[0].new_version == '0.6.0'
