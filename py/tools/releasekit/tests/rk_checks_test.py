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

import subprocess  # noqa: S404 - used to monkeypatch subprocess.run
from pathlib import Path

import pytest
from releasekit.checks import PythonCheckBackend, run_checks
from releasekit.graph import build_graph
from releasekit.preflight import PreflightResult
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


def _make_versioned_packages(
    tmp_path: Path,
    version_a: str,
    version_b: str,
) -> list[Package]:
    """Create two publishable packages with specific requires-python values."""
    pkg_a = tmp_path / 'packages' / 'pkg-a'
    pkg_a.mkdir(parents=True)
    (pkg_a / 'pyproject.toml').write_text(
        f'[project]\nname = "pkg-a"\nversion = "1.0"\nrequires-python = "{version_a}"\n',
        encoding='utf-8',
    )

    pkg_b = tmp_path / 'packages' / 'pkg-b'
    pkg_b.mkdir(parents=True)
    (pkg_b / 'pyproject.toml').write_text(
        f'[project]\nname = "pkg-b"\nversion = "1.0"\nrequires-python = "{version_b}"\n',
        encoding='utf-8',
    )

    return [
        Package(
            name='pkg-a',
            version='1.0',
            path=pkg_a,
            pyproject_path=pkg_a / 'pyproject.toml',
        ),
        Package(
            name='pkg-b',
            version='1.0',
            path=pkg_b,
            pyproject_path=pkg_b / 'pyproject.toml',
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

    # --- python_version_consistency tests ---

    def test_python_version_consistency_pass(self, tmp_path: Path) -> None:
        """All packages with same requires-python passes."""
        packages = _make_versioned_packages(tmp_path, '>=3.10', '>=3.10')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_version_consistency(packages, result)

        if 'python_version' not in result.passed:
            raise AssertionError(f'Expected pass, got: warnings={result.warning_messages}')

    def test_python_version_consistency_mismatch(self, tmp_path: Path) -> None:
        """Packages with different requires-python triggers warning."""
        packages = _make_versioned_packages(tmp_path, '>=3.10', '>=3.11')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_version_consistency(packages, result)

        if 'python_version' not in result.warnings:
            raise AssertionError(f'Expected warning, got: passed={result.passed}')
        msg = result.warning_messages.get('python_version', '')
        if '>=3.10' not in msg or '>=3.11' not in msg:
            raise AssertionError(f'Expected both versions in message, got: {msg}')

    # --- python_classifiers tests ---

    def test_python_classifiers_pass(self, tmp_path: Path) -> None:
        """Package with all expected classifiers passes."""
        pkg_dir = tmp_path / 'packages' / 'good'
        pkg_dir.mkdir(parents=True)
        classifiers_lines = '\n'.join(
            f'  "Programming Language :: Python :: {v}",' for v in ['3.10', '3.11', '3.12', '3.13', '3.14']
        )
        (pkg_dir / 'pyproject.toml').write_text(
            f'[project]\nname = "good"\nversion = "1.0"\nclassifiers = [\n{classifiers_lines}\n]\n',
            encoding='utf-8',
        )
        packages = [
            Package(
                name='good',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_classifiers(packages, result)

        if 'python_classifiers' not in result.passed:
            raise AssertionError(f'Expected pass, got: warnings={result.warning_messages}')

    def test_python_classifiers_missing(self, tmp_path: Path) -> None:
        """Package missing classifiers triggers warning."""
        pkg_dir = tmp_path / 'packages' / 'incomplete'
        pkg_dir.mkdir(parents=True)
        # Only include 3.10 and 3.11, missing 3.12-3.14.
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "incomplete"\nversion = "1.0"\n'
            'classifiers = [\n'
            '  "Programming Language :: Python :: 3.10",\n'
            '  "Programming Language :: Python :: 3.11",\n'
            ']\n',
            encoding='utf-8',
        )
        packages = [
            Package(
                name='incomplete',
                version='1.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_classifiers(packages, result)

        if 'python_classifiers' not in result.warnings:
            raise AssertionError(f'Expected warning, got: passed={result.passed}')
        msg = result.warning_messages.get('python_classifiers', '')
        # Should mention the missing versions.
        if '3.12' not in msg or '3.13' not in msg or '3.14' not in msg:
            raise AssertionError(f'Expected missing versions in message, got: {msg}')

    # --- dependency_resolution tests ---

    def test_dependency_resolution_pass(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Successful uv pip check passes."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=[], returncode=0, stdout='', stderr='')

        monkeypatch.setattr(subprocess, 'run', fake_run)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([], result)

        if 'dependency_resolution' not in result.passed:
            raise AssertionError(f'Expected pass, got: warnings={result.warning_messages}')

    def test_dependency_resolution_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Failed uv pip check triggers warning."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout='missing-pkg 1.0 requires other-pkg, which is not installed.',
                stderr='',
            )

        monkeypatch.setattr(subprocess, 'run', fake_run)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([], result)

        if 'dependency_resolution' not in result.warnings:
            raise AssertionError(f'Expected warning, got: passed={result.passed}')
        msg = result.warning_messages.get('dependency_resolution', '')
        if 'missing-pkg' not in msg:
            raise AssertionError(f'Expected error details in message, got: {msg}')

    def test_dependency_resolution_uv_not_found(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing uv binary triggers a graceful warning, not a crash."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError('uv')

        monkeypatch.setattr(subprocess, 'run', fake_run)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([], result)

        if 'dependency_resolution' not in result.warnings:
            raise AssertionError(f'Expected warning, got: passed={result.passed}')
        msg = result.warning_messages.get('dependency_resolution', '')
        if 'not found' not in msg:
            raise AssertionError(f'Expected "not found" in message, got: {msg}')

    # --- namespace_init tests ---

    def test_namespace_init_clean(self, tmp_path: Path) -> None:
        """Plugin without __init__.py in namespace dirs passes."""
        plugin_dir = tmp_path / 'plugins' / 'clean'
        src_genkit = plugin_dir / 'src' / 'genkit' / 'plugins' / 'clean'
        src_genkit.mkdir(parents=True)
        (src_genkit / '__init__.py').write_text('', encoding='utf-8')
        # No __init__.py in src/genkit/ or src/genkit/plugins/.

        packages = [
            Package(
                name='genkit-plugin-clean',
                version='1.0',
                path=plugin_dir,
                pyproject_path=plugin_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_namespace_init(packages, result)

        if 'namespace_init' not in result.passed:
            raise AssertionError(f'Expected pass, got: errors={result.errors}')

    def test_namespace_init_detected(self, tmp_path: Path) -> None:
        """__init__.py in namespace dir is reported as error."""
        plugin_dir = tmp_path / 'plugins' / 'broken'
        src_genkit = plugin_dir / 'src' / 'genkit'
        src_genkit.mkdir(parents=True)
        # BAD: __init__.py in the namespace directory.
        (src_genkit / '__init__.py').write_text('# bad!', encoding='utf-8')

        packages = [
            Package(
                name='genkit-plugin-broken',
                version='1.0',
                path=plugin_dir,
                pyproject_path=plugin_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_namespace_init(packages, result)

        if 'namespace_init' not in result.failed:
            raise AssertionError(f'Expected failure, got: passed={result.passed}')
        msg = result.errors.get('namespace_init', '')
        if 'genkit-plugin-broken' not in msg:
            raise AssertionError(f'Expected package name in error, got: {msg}')

    def test_namespace_init_plugins_subdir(self, tmp_path: Path) -> None:
        """__init__.py in genkit/plugins/ namespace dir is reported."""
        plugin_dir = tmp_path / 'plugins' / 'bad2'
        src_plugins = plugin_dir / 'src' / 'genkit' / 'plugins'
        src_plugins.mkdir(parents=True)
        # BAD: __init__.py in genkit/plugins/ namespace directory.
        (src_plugins / '__init__.py').write_text('', encoding='utf-8')
        # Also create the actual package dir (fine to have __init__.py here).
        pkg_mod = src_plugins / 'bad2'
        pkg_mod.mkdir()
        (pkg_mod / '__init__.py').write_text('', encoding='utf-8')

        packages = [
            Package(
                name='genkit-plugin-bad2',
                version='1.0',
                path=plugin_dir,
                pyproject_path=plugin_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_namespace_init(packages, result)

        if 'namespace_init' not in result.failed:
            raise AssertionError(f'Expected failure, got: passed={result.passed}')

    def test_namespace_init_skips_non_plugins(self, tmp_path: Path) -> None:
        """Non-plugin packages are not checked for namespace init files."""
        core_dir = tmp_path / 'packages' / 'genkit'
        src_dir = core_dir / 'src' / 'genkit'
        src_dir.mkdir(parents=True)
        # This __init__.py is fine because core packages own the namespace root.
        (src_dir / '__init__.py').write_text('', encoding='utf-8')

        packages = [
            Package(
                name='genkit',
                version='1.0',
                path=core_dir,
                pyproject_path=core_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_namespace_init(packages, result)

        if 'namespace_init' not in result.passed:
            raise AssertionError(f'Expected pass for non-plugin, got: errors={result.errors}')


class TestUngroupedPackages:
    """ungrouped_packages check detects packages not in any config group."""

    def test_all_grouped_passes(self) -> None:
        """When all packages match a group pattern, check passes."""
        packages = [
            Package(name='genkit', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
            Package(name='genkit-plugin-foo', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
        ]
        groups = {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups=groups)
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass, got warnings: {result.warnings}')

    def test_ungrouped_warns(self) -> None:
        """A package not matched by any group pattern triggers a warning."""
        packages = [
            Package(name='genkit', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
            Package(name='new-pkg', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
        ]
        groups = {'core': ['genkit']}
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups=groups)
        if 'ungrouped_packages' not in result.warnings:
            raise AssertionError(f'Expected warning for new-pkg, got: {result.passed}')
        if 'new-pkg' not in result.warning_messages['ungrouped_packages']:
            raise AssertionError(
                f'Expected new-pkg in warning, got: {result.warning_messages["ungrouped_packages"]}',
            )

    def test_empty_groups_passes(self) -> None:
        """When no groups are configured, check passes (nothing to validate)."""
        packages = [
            Package(name='genkit', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups={})
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass for empty groups, got: {result.warnings}')

    def test_wildcard_matches(self) -> None:
        """Wildcard patterns in groups match correctly."""
        packages = [
            Package(name='sample-hello', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
            Package(name='sample-world', version='1.0', path=Path('/x'), pyproject_path=Path('/x/p.toml')),
        ]
        groups = {'samples': ['sample-*']}
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups=groups)
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass for wildcard match, got: {result.warnings}')
