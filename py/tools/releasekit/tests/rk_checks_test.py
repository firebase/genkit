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

"""Tests for releasekit.checks module."""

from __future__ import annotations

from pathlib import Path

from releasekit.checks import PythonCheckBackend, run_checks
from releasekit.graph import build_graph
from releasekit.workspace import Package


def _make_packages(tmp_path: Path) -> list[Package]:
    """Create packages with actual filesystem paths for checks."""
    core_dir = tmp_path / 'packages' / 'genkit'
    core_dir.mkdir(parents=True)
    (core_dir / 'pyproject.toml').write_text(
        '[project]\nname = "genkit"\nversion = "0.5.0"\n'
        'description = "Genkit SDK"\n'
        'license = {text = "Apache-2.0"}\n'
        'authors = [{name = "Google"}]\n',
        encoding='utf-8',
    )
    (core_dir / 'LICENSE').write_text('Apache 2.0', encoding='utf-8')
    (core_dir / 'README.md').write_text('# genkit', encoding='utf-8')

    plugin_dir = tmp_path / 'plugins' / 'foo'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'pyproject.toml').write_text(
        '[project]\nname = "genkit-plugin-foo"\nversion = "0.5.0"\n'
        'description = "Foo plugin"\n'
        'license = {text = "Apache-2.0"}\n'
        'authors = [{name = "Google"}]\n',
        encoding='utf-8',
    )
    (plugin_dir / 'LICENSE').write_text('Apache 2.0', encoding='utf-8')
    (plugin_dir / 'README.md').write_text('# foo', encoding='utf-8')
    # Add py.typed marker.
    src_dir = plugin_dir / 'src' / 'genkit' / 'plugins' / 'foo'
    src_dir.mkdir(parents=True)
    (src_dir / 'py.typed').write_text('', encoding='utf-8')

    return [
        Package(
            name='genkit',
            version='0.5.0',
            path=core_dir,
            pyproject_path=core_dir / 'pyproject.toml',
        ),
        Package(
            name='genkit-plugin-foo',
            version='0.5.0',
            path=plugin_dir,
            pyproject_path=plugin_dir / 'pyproject.toml',
            internal_deps=['genkit'],
        ),
    ]


class TestRunChecks:
    """Tests for run_checks()."""

    def test_clean_workspace(self, tmp_path: Path) -> None:
        """Clean workspace passes all checks."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=PythonCheckBackend())

        if result.errors:
            raise AssertionError(f'Unexpected errors: {result.errors}')

    def test_no_backend(self, tmp_path: Path) -> None:
        """Run with no backend skips language-specific checks."""
        packages = _make_packages(tmp_path)
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        if result.errors:
            raise AssertionError(f'Unexpected errors: {result.errors}')

    def test_cycles_detected(self, tmp_path: Path) -> None:
        """Cycles in the graph are reported as errors."""
        dir_a = tmp_path / 'a'
        dir_a.mkdir()
        dir_b = tmp_path / 'b'
        dir_b.mkdir()
        packages = [
            Package(
                name='a',
                version='1.0.0',
                path=dir_a,
                pyproject_path=dir_a / 'pyproject.toml',
                internal_deps=['b'],
            ),
            Package(
                name='b',
                version='1.0.0',
                path=dir_b,
                pyproject_path=dir_b / 'pyproject.toml',
                internal_deps=['a'],
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        has_cycle_error = any('cycl' in str(e).lower() for e in result.errors)
        if not has_cycle_error:
            raise AssertionError(f'Expected cycle error, got: {result.errors}')

    def test_self_dep_detected(self, tmp_path: Path) -> None:
        """Self-dependency is reported."""
        pkg_dir = tmp_path / 'packages' / 'x'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "x"\nversion = "1.0"',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('MIT', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('# x', encoding='utf-8')

        packages = [
            Package(
                name='x',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
                internal_deps=['x'],
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        has_self_dep = any('self' in str(e).lower() for e in result.errors)
        if not has_self_dep:
            raise AssertionError(f'Expected self-dep error, got: {result.errors}')

    def test_missing_license_detected(self, tmp_path: Path) -> None:
        """Missing LICENSE file is reported."""
        pkg_dir = tmp_path / 'packages' / 'nolicense'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nolicense"\nversion = "1.0"',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('# nolicense', encoding='utf-8')
        # No LICENSE file!

        packages = [
            Package(
                name='nolicense',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        has_license_error = any('license' in str(e).lower() for e in result.errors.values())
        if not has_license_error:
            raise AssertionError(
                f'Expected license error, got: errors={result.errors}, warnings={result.warning_messages}'
            )

    def test_missing_readme_detected(self, tmp_path: Path) -> None:
        """Missing README is reported."""
        pkg_dir = tmp_path / 'packages' / 'noreadme'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "noreadme"\nversion = "1.0"',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('MIT', encoding='utf-8')
        # No README!

        packages = [
            Package(
                name='noreadme',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        has_readme_error = any('readme' in str(e).lower() for e in result.errors.values())
        if not has_readme_error:
            raise AssertionError(
                f'Expected readme error, got: errors={result.errors}, warnings={result.warning_messages}'
            )

    def test_stale_artifacts_detected(self, tmp_path: Path) -> None:
        """Stale .bak and dist/ files are reported."""
        pkg_dir = tmp_path / 'packages' / 'stale'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "stale"\nversion = "1.0"',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('MIT', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('# stale', encoding='utf-8')
        (pkg_dir / 'pyproject.toml.bak').write_text('backup', encoding='utf-8')

        packages = [
            Package(
                name='stale',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None)

        has_stale_warning = any('stale' in str(w).lower() or 'bak' in str(w).lower() for w in result.warnings)
        if not has_stale_warning:
            raise AssertionError(f'Expected stale artifact warning, got: {result.warnings}')


class TestPythonCheckBackend:
    """Tests for PythonCheckBackend."""

    def test_version_consistency_mismatch(self, tmp_path: Path) -> None:
        """Plugin with different version from core triggers warning."""
        core_dir = tmp_path / 'packages' / 'genkit'
        core_dir.mkdir(parents=True)
        (core_dir / 'pyproject.toml').write_text(
            '[project]\nname = "genkit"\nversion = "0.5.0"\n',
            encoding='utf-8',
        )
        (core_dir / 'LICENSE').write_text('Apache', encoding='utf-8')
        (core_dir / 'README.md').write_text('# genkit', encoding='utf-8')

        plugin_dir = tmp_path / 'plugins' / 'bar'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'pyproject.toml').write_text(
            '[project]\nname = "genkit-plugin-bar"\nversion = "0.4.0"\n',
            encoding='utf-8',
        )
        (plugin_dir / 'LICENSE').write_text('Apache', encoding='utf-8')
        (plugin_dir / 'README.md').write_text('# bar', encoding='utf-8')

        packages = [
            Package(
                name='genkit',
                version='0.5.0',
                path=core_dir,
                pyproject_path=core_dir / 'pyproject.toml',
            ),
            Package(
                name='genkit-plugin-bar',
                version='0.4.0',
                path=plugin_dir,
                pyproject_path=plugin_dir / 'pyproject.toml',
                internal_deps=['genkit'],
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=PythonCheckBackend())

        has_version_warning = any('version' in str(w).lower() for w in result.warnings)
        if not has_version_warning:
            raise AssertionError(f'Expected version mismatch warning, got: {result.warnings}')
