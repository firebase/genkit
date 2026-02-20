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

"""Tests for :class:`releasekit.backends.workspace.bazel.BazelWorkspace`."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace import Workspace
from releasekit.backends.workspace.bazel import BazelWorkspace

# Fixtures

_MODULE_BAZEL = """\
module(
    name = "my_project",
    version = "1.2.3",
)

bazel_dep(name = "rules_jvm_external", version = "6.0")
bazel_dep(name = "rules_java", version = "7.0")
"""

_BUILD_CORE = """\
java_library(
    name = "core-lib",
    srcs = glob(["src/**/*.java"]),
)

java_export(
    name = "core",
    maven_coordinates = "com.example:core:{pom_version}",
    version = "1.2.3",
)
"""

_BUILD_PLUGIN = """\
java_export(
    name = "plugin-google",
    maven_coordinates = "com.example:plugin-google:{pom_version}",
    version = "1.2.3",
    deps = [":core"],
)
"""

_BUILD_NO_PUBLISH = """\
java_library(
    name = "internal-utils",
    srcs = glob(["src/**/*.java"]),
)
"""

_VERSION_BZL = """\
VERSION = "1.2.3"
"""


def _create_bazel_workspace(root: Path) -> None:
    """Create a minimal Bazel workspace for testing."""
    (root / 'MODULE.bazel').write_text(_MODULE_BAZEL, encoding='utf-8')

    core = root / 'core'
    core.mkdir()
    (core / 'BUILD.bazel').write_text(_BUILD_CORE, encoding='utf-8')

    plugin = root / 'plugins' / 'google'
    plugin.mkdir(parents=True)
    (plugin / 'BUILD.bazel').write_text(_BUILD_PLUGIN, encoding='utf-8')

    internal = root / 'internal'
    internal.mkdir()
    (internal / 'BUILD.bazel').write_text(_BUILD_NO_PUBLISH, encoding='utf-8')


# Protocol compliance


class TestBazelWorkspaceProtocol:
    """Verify BazelWorkspace satisfies the Workspace protocol."""

    def test_is_instance_of_protocol(self, tmp_path: Path) -> None:
        """BazelWorkspace should be a runtime-checkable Workspace."""
        ws = BazelWorkspace(workspace_root=tmp_path)
        assert isinstance(ws, Workspace)


# Discover


class TestBazelWorkspaceDiscover:
    """Tests for BazelWorkspace.discover()."""

    @pytest.mark.asyncio
    async def test_discover_finds_publishable_targets(self, tmp_path: Path) -> None:
        """discover() should find java_export targets."""
        _create_bazel_workspace(tmp_path)
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin-google' in names

    @pytest.mark.asyncio
    async def test_discover_excludes_non_publishable(self, tmp_path: Path) -> None:
        """discover() should not include java_library-only targets."""
        _create_bazel_workspace(tmp_path)
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'internal-utils' not in names

    @pytest.mark.asyncio
    async def test_discover_sorted_by_name(self, tmp_path: Path) -> None:
        """discover() should return packages sorted by name."""
        _create_bazel_workspace(tmp_path)
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_discover_with_exclude_patterns(self, tmp_path: Path) -> None:
        """discover() should respect exclude_patterns."""
        _create_bazel_workspace(tmp_path)
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover(exclude_patterns=['plugin-*'])
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin-google' not in names

    @pytest.mark.asyncio
    async def test_discover_empty_workspace(self, tmp_path: Path) -> None:
        """discover() on empty workspace should return empty list."""
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert packages == []

    @pytest.mark.asyncio
    async def test_discover_uses_root_version_as_fallback(self, tmp_path: Path) -> None:
        """discover() should use MODULE.bazel version when target has no version."""
        (tmp_path / 'MODULE.bazel').write_text(
            'module(name = "proj", version = "3.0.0")\n',
            encoding='utf-8',
        )
        pkg = tmp_path / 'lib'
        pkg.mkdir()
        # java_export without version attribute.
        (pkg / 'BUILD.bazel').write_text(
            'java_export(\n    name = "my-lib",\n)\n',
            encoding='utf-8',
        )
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].version == '3.0.0'

    @pytest.mark.asyncio
    async def test_discover_version_from_target(self, tmp_path: Path) -> None:
        """discover() should use target version when present."""
        _create_bazel_workspace(tmp_path)
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.version == '1.2.3'

    @pytest.mark.asyncio
    async def test_discover_deduplicates_names(self, tmp_path: Path) -> None:
        """discover() should not return duplicate package names."""
        (tmp_path / 'MODULE.bazel').write_text(
            'module(name = "proj", version = "1.0.0")\n',
            encoding='utf-8',
        )
        pkg = tmp_path / 'lib'
        pkg.mkdir()
        # Two publish rules with the same name in one BUILD file.
        (pkg / 'BUILD.bazel').write_text(
            'java_export(name = "dup")\nnpm_package(name = "dup")\n',
            encoding='utf-8',
        )
        ws = BazelWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1


# Rewrite version


class TestBazelWorkspaceRewriteVersion:
    """Tests for BazelWorkspace.rewrite_version()."""

    @pytest.mark.asyncio
    async def test_rewrite_module_bazel_version(self, tmp_path: Path) -> None:
        """rewrite_version() should update version in MODULE.bazel."""
        module_path = tmp_path / 'MODULE.bazel'
        module_path.write_text(_MODULE_BAZEL, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(module_path, '2.0.0')
        assert old == '1.2.3'
        new_text = module_path.read_text(encoding='utf-8')
        assert '2.0.0' in new_text
        assert '1.2.3' not in new_text

    @pytest.mark.asyncio
    async def test_rewrite_version_bzl(self, tmp_path: Path) -> None:
        """rewrite_version() should update VERSION in version.bzl."""
        bzl_path = tmp_path / 'version.bzl'
        bzl_path.write_text(_VERSION_BZL, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(bzl_path, '2.0.0')
        assert old == '1.2.3'
        new_text = bzl_path.read_text(encoding='utf-8')
        assert 'VERSION = "2.0.0"' in new_text

    @pytest.mark.asyncio
    async def test_rewrite_build_version(self, tmp_path: Path) -> None:
        """rewrite_version() should update version in BUILD.bazel."""
        build_path = tmp_path / 'BUILD.bazel'
        build_path.write_text(_BUILD_CORE, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(build_path, '2.0.0')
        assert old == '1.2.3'
        new_text = build_path.read_text(encoding='utf-8')
        assert 'version = "2.0.0"' in new_text

    @pytest.mark.asyncio
    async def test_rewrite_version_idempotent(self, tmp_path: Path) -> None:
        """rewrite_version() called twice should be idempotent."""
        module_path = tmp_path / 'MODULE.bazel'
        module_path.write_text(_MODULE_BAZEL, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        await ws.rewrite_version(module_path, '2.0.0')
        text_after_first = module_path.read_text(encoding='utf-8')
        await ws.rewrite_version(module_path, '2.0.0')
        text_after_second = module_path.read_text(encoding='utf-8')
        assert text_after_first == text_after_second


# Rewrite dependency version


class TestBazelWorkspaceRewriteDependencyVersion:
    """Tests for BazelWorkspace.rewrite_dependency_version()."""

    @pytest.mark.asyncio
    async def test_rewrite_bazel_dep_version(self, tmp_path: Path) -> None:
        """rewrite_dependency_version() should update bazel_dep version."""
        module_path = tmp_path / 'MODULE.bazel'
        module_path.write_text(_MODULE_BAZEL, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(module_path, 'rules_jvm_external', '7.0')
        new_text = module_path.read_text(encoding='utf-8')
        assert 'version = "7.0"' in new_text

    @pytest.mark.asyncio
    async def test_rewrite_dep_no_match(self, tmp_path: Path) -> None:
        """rewrite_dependency_version() with nonexistent dep should be a no-op."""
        module_path = tmp_path / 'MODULE.bazel'
        module_path.write_text(_MODULE_BAZEL, encoding='utf-8')
        ws = BazelWorkspace(workspace_root=tmp_path)
        original = module_path.read_text(encoding='utf-8')
        await ws.rewrite_dependency_version(module_path, 'nonexistent_dep', '9.9.9')
        assert module_path.read_text(encoding='utf-8') == original
