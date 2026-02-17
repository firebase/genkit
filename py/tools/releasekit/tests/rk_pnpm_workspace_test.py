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

"""Tests for the pnpm workspace backend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from releasekit.backends.workspace.pnpm import (
    PnpmWorkspace,
    _is_workspace_dep,
    _normalize_name,
    _parse_yaml_simple,
)
from releasekit.errors import ReleaseKitError


class TestParseYamlSimple:
    """Tests for the minimal YAML parser."""

    def test_basic_packages(self) -> None:
        """Parse a standard pnpm-workspace.yaml with packages key."""
        text = "packages:\n  - 'packages/*'\n  - 'plugins/*'\n"
        result = _parse_yaml_simple(text)
        assert result == {'packages': ['packages/*', 'plugins/*']}

    def test_double_quotes(self) -> None:
        """Parse values with double quotes."""
        text = 'packages:\n  - "packages/*"\n'
        result = _parse_yaml_simple(text)
        assert result == {'packages': ['packages/*']}

    def test_no_quotes(self) -> None:
        """Parse values without quotes."""
        text = 'packages:\n  - packages/*\n'
        result = _parse_yaml_simple(text)
        assert result == {'packages': ['packages/*']}

    def test_comments_and_blanks(self) -> None:
        """Skip comments and blank lines."""
        text = "# A comment\n\npackages:\n  # Another comment\n  - 'src/*'\n\n"
        result = _parse_yaml_simple(text)
        assert result == {'packages': ['src/*']}

    def test_exclusion_patterns(self) -> None:
        """Parse exclusion patterns (prefixed with !)."""
        text = "packages:\n  - 'packages/*'\n  - '!packages/scratch'\n"
        result = _parse_yaml_simple(text)
        assert result == {'packages': ['packages/*', '!packages/scratch']}

    def test_empty_yaml(self) -> None:
        """Empty YAML returns empty dict."""
        result = _parse_yaml_simple('')
        assert result == {}

    def test_comments_only(self) -> None:
        """YAML with only comments returns empty dict."""
        result = _parse_yaml_simple('# just a comment\n# another one\n')
        assert result == {}


class TestIsWorkspaceDep:
    """Tests for workspace protocol detection."""

    def test_workspace_star(self) -> None:
        """Detect workspace:* protocol."""
        assert _is_workspace_dep('workspace:*') is True

    def test_workspace_caret(self) -> None:
        """Detect workspace:^ protocol."""
        assert _is_workspace_dep('workspace:^') is True

    def test_workspace_tilde(self) -> None:
        """Detect workspace:~ protocol."""
        assert _is_workspace_dep('workspace:~') is True

    def test_semver_range(self) -> None:
        """Regular semver ranges are not workspace deps."""
        assert _is_workspace_dep('^1.2.3') is False

    def test_exact_version(self) -> None:
        """Exact versions are not workspace deps."""
        assert _is_workspace_dep('1.0.0') is False

    def test_workspace_with_version(self) -> None:
        """workspace:^1.0.0 is a workspace dep (matches workspace:^ prefix)."""
        assert _is_workspace_dep('workspace:^1.0.0') is True


class TestNormalizeName:
    """Tests for npm name normalization."""

    def test_lowercase(self) -> None:
        """Names are lowercased for comparison."""
        assert _normalize_name('MyPackage') == 'mypackage'

    def test_scoped(self) -> None:
        """Scoped package names are lowercased."""
        assert _normalize_name('@genkit-ai/Core') == '@genkit-ai/core'

    def test_already_lower(self) -> None:
        """Already-lowercase names are unchanged."""
        assert _normalize_name('genkit') == 'genkit'


def _write_pnpm_workspace(root: Path, packages: list[str]) -> None:
    """Write a pnpm-workspace.yaml with the given package globs."""
    lines = ['packages:']
    for pkg in packages:
        lines.append(f"  - '{pkg}'")
    (root / 'pnpm-workspace.yaml').write_text('\n'.join(lines) + '\n')


def _write_package_json(
    root: Path,
    subdir: str,
    name: str,
    version: str = '1.0.0',
    deps: dict[str, str] | None = None,
    dev_deps: dict[str, str] | None = None,
    private: bool = False,
) -> Path:
    """Write a package.json in the given subdirectory."""
    pkg_dir = root / subdir
    pkg_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {
        'name': name,
        'version': version,
    }
    if deps:
        data['dependencies'] = deps
    if dev_deps:
        data['devDependencies'] = dev_deps
    if private:
        data['private'] = True
    (pkg_dir / 'package.json').write_text(json.dumps(data, indent=2) + '\n')
    return pkg_dir


class TestPnpmWorkspaceDiscover:
    """PnpmWorkspace.discover() finds packages from pnpm-workspace.yaml."""

    @pytest.mark.asyncio
    async def test_single_package(self, tmp_path: Path) -> None:
        """A single workspace member is discovered."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/core', 'genkit', '1.0.0')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        assert len(pkgs) == 1
        assert pkgs[0].name == 'genkit'
        assert pkgs[0].version == '1.0.0'

    @pytest.mark.asyncio
    async def test_multiple_globs(self, tmp_path: Path) -> None:
        """Multiple member globs discover packages from all dirs."""
        _write_pnpm_workspace(tmp_path, ['packages/*', 'plugins/*'])
        _write_package_json(tmp_path, 'packages/core', '@genkit-ai/core')
        _write_package_json(tmp_path, 'plugins/auth', '@genkit-ai/plugin-auth')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert names == ['@genkit-ai/core', '@genkit-ai/plugin-auth']

    @pytest.mark.asyncio
    async def test_sorted_by_name(self, tmp_path: Path) -> None:
        """Packages are returned sorted by name."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/zebra', 'zebra')
        _write_package_json(tmp_path, 'packages/alpha', 'alpha')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        assert [p.name for p in pkgs] == ['alpha', 'zebra']

    @pytest.mark.asyncio
    async def test_exclusion_pattern(self, tmp_path: Path) -> None:
        """Directories matching ! patterns are excluded."""
        _write_pnpm_workspace(tmp_path, ['packages/*', '!packages/scratch'])
        _write_package_json(tmp_path, 'packages/core', 'core')
        _write_package_json(tmp_path, 'packages/scratch', 'scratch')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        assert len(pkgs) == 1
        assert pkgs[0].name == 'core'

    @pytest.mark.asyncio
    async def test_exclude_by_name_pattern(self, tmp_path: Path) -> None:
        """Exclude patterns filter by package name."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/core', 'core')
        _write_package_json(tmp_path, 'packages/test-app', 'test-app')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['test-*'])

        assert len(pkgs) == 1
        assert pkgs[0].name == 'core'

    @pytest.mark.asyncio
    async def test_private_package_not_publishable(self, tmp_path: Path) -> None:
        """Packages with "private": true are marked as not publishable."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/internal', 'internal', private=True)
        _write_package_json(tmp_path, 'packages/public', 'public')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        internal = next(p for p in pkgs if p.name == 'internal')
        public = next(p for p in pkgs if p.name == 'public')

        assert internal.is_publishable is False
        assert public.is_publishable is True


class TestPnpmWorkspaceDiscoverDeps:
    """PnpmWorkspace.discover() classifies internal vs external deps."""

    @pytest.mark.asyncio
    async def test_workspace_protocol_is_internal(self, tmp_path: Path) -> None:
        """Dependencies using workspace:* protocol are internal."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/core', '@genkit-ai/core')
        _write_package_json(
            tmp_path,
            'packages/genkit',
            'genkit',
            deps={'@genkit-ai/core': 'workspace:*'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        genkit_pkg = next(p for p in pkgs if p.name == 'genkit')
        assert genkit_pkg.internal_deps == ['@genkit-ai/core']

    @pytest.mark.asyncio
    async def test_workspace_caret_is_internal(self, tmp_path: Path) -> None:
        """Dependencies using workspace:^ protocol are internal."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/core', 'core')
        _write_package_json(
            tmp_path,
            'packages/plugin',
            'plugin',
            deps={'core': 'workspace:^'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        plugin = next(p for p in pkgs if p.name == 'plugin')
        assert plugin.internal_deps == ['core']

    @pytest.mark.asyncio
    async def test_semver_range_is_external(self, tmp_path: Path) -> None:
        """Dependencies with semver ranges are external."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(
            tmp_path,
            'packages/app',
            'app',
            deps={'express': '^4.18.0', 'uuid': '~10.0.0'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        app = pkgs[0]
        assert sorted(app.external_deps) == ['express', 'uuid']
        assert app.internal_deps == []

    @pytest.mark.asyncio
    async def test_devdeps_classified(self, tmp_path: Path) -> None:
        """DevDependencies are also classified."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        _write_package_json(tmp_path, 'packages/core', 'core')
        _write_package_json(
            tmp_path,
            'packages/app',
            'app',
            deps={'core': 'workspace:*'},
            dev_deps={'typescript': '^5.0.0'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        app = next(p for p in pkgs if p.name == 'app')
        assert app.internal_deps == ['core']
        assert 'typescript' in app.external_deps


class TestPnpmWorkspaceDiscoverErrors:
    """PnpmWorkspace.discover() error handling."""

    @pytest.mark.asyncio
    async def test_missing_workspace_yaml(self, tmp_path: Path) -> None:
        """Error when pnpm-workspace.yaml doesn't exist."""
        ws = PnpmWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError):
            await ws.discover()

    @pytest.mark.asyncio
    async def test_no_members(self, tmp_path: Path) -> None:
        """Error when no packages key exists."""
        (tmp_path / 'pnpm-workspace.yaml').write_text('# empty\n')
        ws = PnpmWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError, match='No packages'):
            await ws.discover()

    @pytest.mark.asyncio
    async def test_no_matching_dirs(self, tmp_path: Path) -> None:
        """Error when globs match no directories."""
        _write_pnpm_workspace(tmp_path, ['nonexistent/*'])
        ws = PnpmWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError, match='No packages found'):
            await ws.discover()

    @pytest.mark.asyncio
    async def test_duplicate_package_name(self, tmp_path: Path) -> None:
        """Error when two packages have the same name."""
        _write_pnpm_workspace(tmp_path, ['packages/*', 'plugins/*'])
        _write_package_json(tmp_path, 'packages/core', 'dupe')
        _write_package_json(tmp_path, 'plugins/core', 'dupe')

        ws = PnpmWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError, match='Duplicate'):
            await ws.discover()

    @pytest.mark.asyncio
    async def test_missing_name_in_package_json(self, tmp_path: Path) -> None:
        """Nameless package.json is silently skipped (workspace-root pattern)."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        pkg_dir = tmp_path / 'packages' / 'bad'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'package.json').write_text('{"version": "1.0.0"}')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        # The nameless package is skipped; no packages remain.
        assert len(pkgs) == 0


class TestPnpmWorkspaceRewrite:
    """PnpmWorkspace version rewriting methods."""

    @pytest.mark.asyncio
    async def test_rewrite_version(self, tmp_path: Path) -> None:
        """Rewrite version in package.json."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        pkg_dir = _write_package_json(tmp_path, 'packages/core', 'core', '1.0.0')
        manifest = pkg_dir / 'package.json'

        ws = PnpmWorkspace(tmp_path)
        old = await ws.rewrite_version(manifest, '2.0.0')

        assert old == '1.0.0'

        # Verify the file was updated.
        data = json.loads(manifest.read_text())
        assert data['version'] == '2.0.0'
        assert data['name'] == 'core'  # Other fields preserved.

    @pytest.mark.asyncio
    async def test_rewrite_version_returns_old(self, tmp_path: Path) -> None:
        """rewrite_version returns the old version string."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        pkg_dir = _write_package_json(tmp_path, 'packages/core', 'core', '3.1.4')
        manifest = pkg_dir / 'package.json'

        ws = PnpmWorkspace(tmp_path)
        old = await ws.rewrite_version(manifest, '3.2.0')

        assert old == '3.1.4'

    @pytest.mark.asyncio
    async def test_rewrite_version_no_version_key(self, tmp_path: Path) -> None:
        """Error when package.json has no version field."""
        pkg_dir = tmp_path / 'pkg'
        pkg_dir.mkdir()
        manifest = pkg_dir / 'package.json'
        manifest.write_text('{"name": "core"}')

        ws = PnpmWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError, match='No "version"'):
            await ws.rewrite_version(manifest, '1.0.0')

    @pytest.mark.asyncio
    async def test_rewrite_dependency_version(self, tmp_path: Path) -> None:
        """Rewrite a workspace dep's version in package.json."""
        _write_pnpm_workspace(tmp_path, ['packages/*'])
        pkg_dir = _write_package_json(
            tmp_path,
            'packages/app',
            'app',
            deps={'@genkit-ai/core': 'workspace:*', 'express': '^4.0.0'},
        )
        manifest = pkg_dir / 'package.json'

        ws = PnpmWorkspace(tmp_path)
        await ws.rewrite_dependency_version(manifest, '@genkit-ai/core', '1.5.0')

        data = json.loads(manifest.read_text())
        assert data['dependencies']['@genkit-ai/core'] == '^1.5.0'
        assert data['dependencies']['express'] == '^4.0.0'  # Unchanged.

    @pytest.mark.asyncio
    async def test_rewrite_dependency_in_devdeps(self, tmp_path: Path) -> None:
        """Rewrite dep version across devDependencies too."""
        pkg_dir = tmp_path / 'pkg'
        pkg_dir.mkdir()
        manifest = pkg_dir / 'package.json'
        manifest.write_text(
            json.dumps({
                'name': 'app',
                'version': '1.0.0',
                'devDependencies': {'core': 'workspace:^'},
            })
            + '\n'
        )

        ws = PnpmWorkspace(tmp_path)
        await ws.rewrite_dependency_version(manifest, 'core', '2.0.0')

        data = json.loads(manifest.read_text())
        assert data['devDependencies']['core'] == '^2.0.0'

    @pytest.mark.asyncio
    async def test_rewrite_nonexistent_dep_is_noop(self, tmp_path: Path) -> None:
        """Rewriting a dep that doesn't exist has no effect."""
        pkg_dir = tmp_path / 'pkg'
        pkg_dir.mkdir()
        manifest = pkg_dir / 'package.json'
        original = json.dumps({'name': 'app', 'version': '1.0.0', 'dependencies': {}})
        manifest.write_text(original + '\n')

        ws = PnpmWorkspace(tmp_path)
        await ws.rewrite_dependency_version(manifest, 'nonexistent', '1.0.0')

        # File unchanged (only whitespace differences from json.dumps).
        data = json.loads(manifest.read_text())
        assert data['dependencies'] == {}


class TestPnpmWorkspaceGenkitJs:
    """Test with a structure mimicking the real genkit JS workspace."""

    @pytest.mark.asyncio
    async def test_genkit_js_like_workspace(self, tmp_path: Path) -> None:
        """Simulate the genkit JS workspace structure."""
        _write_pnpm_workspace(tmp_path, ['./*', 'plugins/*', '!./scripts'])

        # Root-level packages (like genkit/js/genkit, genkit/js/ai, genkit/js/core).
        _write_package_json(
            tmp_path,
            'genkit',
            'genkit',
            '1.28.0',
            deps={
                '@genkit-ai/ai': 'workspace:*',
                '@genkit-ai/core': 'workspace:*',
                'uuid': '^10.0.0',
            },
        )
        _write_package_json(tmp_path, 'ai', '@genkit-ai/ai', '1.28.0')
        _write_package_json(tmp_path, 'core', '@genkit-ai/core', '1.28.0')

        # Plugin.
        _write_package_json(
            tmp_path,
            'plugins/google-genai',
            '@genkit-ai/google-ai',
            '1.28.0',
            deps={'genkit': 'workspace:^', '@google/generative-ai': '^0.21.0'},
        )

        # Scripts dir (should be excluded).
        scripts_dir = tmp_path / 'scripts'
        scripts_dir.mkdir()
        (scripts_dir / 'package.json').write_text(
            json.dumps({
                'name': 'scripts',
                'version': '0.0.0',
                'private': True,
            })
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert 'scripts' not in names
        assert '@genkit-ai/ai' in names
        assert '@genkit-ai/core' in names
        assert 'genkit' in names
        assert '@genkit-ai/google-ai' in names

        # Verify dependency classification.
        genkit_pkg = next(p for p in pkgs if p.name == 'genkit')
        assert sorted(genkit_pkg.internal_deps) == ['@genkit-ai/ai', '@genkit-ai/core']
        assert genkit_pkg.external_deps == ['uuid']

        plugin_pkg = next(p for p in pkgs if p.name == '@genkit-ai/google-ai')
        assert plugin_pkg.internal_deps == ['genkit']
        assert plugin_pkg.external_deps == ['@google/generative-ai']


class TestPnpmWorkspaceDotPatterns:
    """Tests for pnpm workspace patterns with '.' and './' prefixes.

    These are real patterns found in genkit's monorepo that caused
    ``pathlib.glob()`` to crash with ``IndexError: tuple index out of range``.
    """

    @pytest.mark.asyncio
    async def test_dot_pattern_root_as_package(self, tmp_path: Path) -> None:
        """'.' pattern treats the workspace root itself as a package."""
        _write_pnpm_workspace(tmp_path, ['.', 'plugins/*'])

        # The root is itself a package (genkit-tools pattern).
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'genkit-tools', 'version': '1.0.0'}) + '\n')

        _write_package_json(
            tmp_path,
            'plugins/auth',
            '@genkit-ai/tools-plugin-auth',
            deps={'genkit-tools': 'workspace:*'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert 'genkit-tools' in names
        assert '@genkit-ai/tools-plugin-auth' in names

    @pytest.mark.asyncio
    async def test_dot_slash_star_pattern(self, tmp_path: Path) -> None:
        """./* pattern expands to immediate child directories."""
        _write_pnpm_workspace(tmp_path, ['./*', 'plugins/*'])

        _write_package_json(tmp_path, 'core', 'core')
        _write_package_json(tmp_path, 'utils', 'utils')
        _write_package_json(tmp_path, 'plugins/auth', 'plugin-auth')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert names == ['core', 'plugin-auth', 'utils']

    @pytest.mark.asyncio
    async def test_dot_slash_exclusion_pattern(self, tmp_path: Path) -> None:
        """!./scripts exclusion pattern correctly strips the ./ prefix."""
        _write_pnpm_workspace(tmp_path, ['./*', '!./scripts'])

        _write_package_json(tmp_path, 'core', 'core')
        scripts_dir = tmp_path / 'scripts'
        scripts_dir.mkdir()
        (scripts_dir / 'package.json').write_text(json.dumps({'name': 'scripts', 'version': '0.0.0', 'private': True}))

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = [p.name for p in pkgs]
        assert 'core' in names
        assert 'scripts' not in names

    @pytest.mark.asyncio
    async def test_bare_directory_names(self, tmp_path: Path) -> None:
        """Bare directory names (no glob) are valid pnpm patterns."""
        _write_pnpm_workspace(tmp_path, ['.', 'cli', 'common', 'plugins/*'])

        (tmp_path / 'package.json').write_text(json.dumps({'name': 'root-pkg', 'version': '1.0.0'}) + '\n')
        _write_package_json(tmp_path, 'cli', 'cli-tool')
        _write_package_json(tmp_path, 'common', 'common-utils')
        _write_package_json(tmp_path, 'plugins/auth', 'plugin-auth')

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert names == ['cli-tool', 'common-utils', 'plugin-auth', 'root-pkg']

    @pytest.mark.asyncio
    async def test_genkit_tools_like_workspace(self, tmp_path: Path) -> None:
        """Simulate the genkit-tools workspace structure (caused real crash)."""
        _write_pnpm_workspace(
            tmp_path,
            ['.', 'cli', 'common', 'telemetry-server', 'plugins/*'],
        )

        (tmp_path / 'package.json').write_text(
            json.dumps({
                'name': '@genkit-ai/tools-common',
                'version': '1.8.0',
                'private': True,
            })
            + '\n'
        )
        _write_package_json(tmp_path, 'cli', '@genkit-ai/cli', '1.8.0')
        _write_package_json(
            tmp_path,
            'common',
            '@genkit-ai/tools-plugins',
            '1.8.0',
            deps={'@genkit-ai/cli': 'workspace:*'},
        )
        _write_package_json(tmp_path, 'telemetry-server', '@genkit-ai/telemetry-server', '1.8.0')
        _write_package_json(
            tmp_path,
            'plugins/dotprompt',
            '@genkit-ai/dotprompt',
            '1.8.0',
            deps={'@genkit-ai/cli': 'workspace:^'},
        )

        ws = PnpmWorkspace(tmp_path)
        pkgs = await ws.discover()

        names = sorted(p.name for p in pkgs)
        assert '@genkit-ai/cli' in names
        assert '@genkit-ai/tools-common' in names
        assert '@genkit-ai/tools-plugins' in names
        assert '@genkit-ai/telemetry-server' in names
        assert '@genkit-ai/dotprompt' in names

        # Verify internal dep classification through '.' root package.
        plugins_pkg = next(p for p in pkgs if p.name == '@genkit-ai/tools-plugins')
        assert plugins_pkg.internal_deps == ['@genkit-ai/cli']
