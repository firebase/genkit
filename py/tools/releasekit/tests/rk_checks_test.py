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
from typing import Any

import pytest
import tomlkit
from releasekit.checks import (
    DEPRECATED_CLASSIFIERS,
    PythonCheckBackend,
    fix_build_system,
    fix_changelog_url,
    fix_deprecated_classifiers,
    fix_duplicate_dependencies,
    fix_license_classifier_mismatch,
    fix_missing_license,
    fix_missing_readme,
    fix_namespace_init,
    fix_placeholder_urls,
    fix_publish_classifiers,
    fix_readme_content_type,
    fix_readme_field,
    fix_requires_python,
    fix_self_dependencies,
    fix_stale_artifacts,
    fix_type_markers,
    fix_version_field,
    run_checks,
)
from releasekit.graph import build_graph
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package


def _read_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file, returning a plain dict for type-safe subscripting.

    ``tomlkit.parse()`` returns ``TOMLDocument`` whose ``__getitem__``
    yields ``Item | Container`` — a union that ``ty`` cannot subscript.
    Converting to a plain ``dict`` via ``tomlkit.unwrap()`` gives us
    standard Python dicts/lists that all type checkers handle correctly.
    """
    doc = tomlkit.parse(path.read_text(encoding='utf-8'))
    return doc.unwrap()


def _make_packages(tmp_path: Path) -> list[Package]:
    """Create packages with actual filesystem paths for checks."""
    core_dir = tmp_path / 'packages' / 'genkit'
    core_dir.mkdir(parents=True)
    (core_dir / 'pyproject.toml').write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[project]\nname = "genkit"\nversion = "0.5.0"\n'
        'requires-python = ">=3.10"\n'
        'readme = "README.md"\n'
        'description = "Genkit SDK"\n'
        'license = {text = "Apache-2.0"}\n'
        'authors = [{name = "Google"}]\n'
        'classifiers = ["License :: OSI Approved :: Apache Software License", "Typing :: Typed"]\n'
        'keywords = ["python"]\n\n'
        '[project.urls]\n'
        'Changelog = "https://github.com/example/genkit/CHANGELOG.md"\n'
        'Homepage = "https://github.com/example/genkit"\n'
        'Repository = "https://github.com/example/genkit"\n'
        '"Bug Tracker" = "https://github.com/example/genkit/issues"\n',
        encoding='utf-8',
    )
    (core_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
    (core_dir / 'README.md').write_text('# genkit', encoding='utf-8')

    plugin_dir = tmp_path / 'plugins' / 'foo'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'pyproject.toml').write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[project]\nname = "genkit-plugin-foo"\nversion = "0.5.0"\n'
        'requires-python = ">=3.10"\n'
        'readme = "README.md"\n'
        'description = "Foo plugin"\n'
        'license = {text = "Apache-2.0"}\n'
        'authors = [{name = "Google"}]\n'
        'classifiers = ["License :: OSI Approved :: Apache Software License", "Typing :: Typed"]\n'
        'keywords = ["python"]\n\n'
        '[project.urls]\n'
        'Changelog = "https://github.com/example/genkit/CHANGELOG.md"\n'
        'Homepage = "https://github.com/example/genkit"\n'
        'Repository = "https://github.com/example/genkit"\n'
        '"Bug Tracker" = "https://github.com/example/genkit/issues"\n',
        encoding='utf-8',
    )
    (plugin_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
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
            manifest_path=core_dir / 'pyproject.toml',
        ),
        Package(
            name='genkit-plugin-foo',
            version='0.5.0',
            path=plugin_dir,
            manifest_path=plugin_dir / 'pyproject.toml',
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
            manifest_path=pkg_a / 'pyproject.toml',
        ),
        Package(
            name='pkg-b',
            version='1.0',
            path=pkg_b,
            manifest_path=pkg_b / 'pyproject.toml',
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
                manifest_path=dir_a / 'pyproject.toml',
                internal_deps=['b'],
            ),
            Package(
                name='b',
                version='1.0.0',
                path=dir_b,
                manifest_path=dir_b / 'pyproject.toml',
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
                manifest_path=pkg_dir / 'pyproject.toml',
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
                manifest_path=pkg_dir / 'pyproject.toml',
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
                manifest_path=pkg_dir / 'pyproject.toml',
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
                manifest_path=pkg_dir / 'pyproject.toml',
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
                manifest_path=core_dir / 'pyproject.toml',
            ),
            Package(
                name='genkit-plugin-bar',
                version='0.4.0',
                path=plugin_dir,
                manifest_path=plugin_dir / 'pyproject.toml',
                internal_deps=['genkit'],
            ),
        ]
        graph = build_graph(packages)
        result = run_checks(
            packages,
            graph,
            backend=PythonCheckBackend(
                core_package='genkit',
                plugin_prefix='genkit-plugin-',
            ),
        )

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
                manifest_path=pkg_dir / 'pyproject.toml',
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
                manifest_path=pkg_dir / 'pyproject.toml',
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
            """Fake run."""
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
            """Fake run."""
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
            """Fake run."""
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
                manifest_path=plugin_dir / 'pyproject.toml',
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
                manifest_path=plugin_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend(namespace_dirs=['genkit', 'genkit/plugins'])
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
                manifest_path=plugin_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend(namespace_dirs=['genkit', 'genkit/plugins'])
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
                manifest_path=core_dir / 'pyproject.toml',
            ),
        ]
        backend = PythonCheckBackend(
            namespace_dirs=['genkit', 'genkit/plugins'],
            plugin_dirs=['plugins'],
        )
        result = PreflightResult()
        backend.check_namespace_init(packages, result)

        if 'namespace_init' not in result.passed:
            raise AssertionError(f'Expected pass for non-plugin, got: errors={result.errors}')


class TestUngroupedPackages:
    """ungrouped_packages check detects packages not in any config group."""

    def test_all_grouped_passes(self) -> None:
        """When all packages match a group pattern, check passes."""
        packages = [
            Package(name='genkit', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
            Package(name='genkit-plugin-foo', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
        ]
        groups = {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups=groups)
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass, got warnings: {result.warnings}')

    def test_ungrouped_warns(self) -> None:
        """A package not matched by any group pattern triggers a warning."""
        packages = [
            Package(name='genkit', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
            Package(name='new-pkg', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
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
            Package(name='genkit', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
        ]
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups={})
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass for empty groups, got: {result.warnings}')

    def test_wildcard_matches(self) -> None:
        """Wildcard patterns in groups match correctly."""
        packages = [
            Package(name='sample-hello', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
            Package(name='sample-world', version='1.0', path=Path('/x'), manifest_path=Path('/x/p.toml')),
        ]
        groups = {'samples': ['sample-*']}
        graph = build_graph(packages)
        result = run_checks(packages, graph, backend=None, groups=groups)
        if 'ungrouped_packages' not in result.passed:
            raise AssertionError(f'Expected pass for wildcard match, got: {result.warnings}')


class TestFixPublishClassifiers:
    """Tests for fix_publish_classifiers()."""

    _TOML_WITH_PRIVATE = (
        '[project]\n'
        'name = "pkg-a"\n'
        'version = "1.0"\n'
        'classifiers = [\n'
        '  "Development Status :: 3 - Alpha",\n'
        '  "License :: OSI Approved :: Apache Software License",\n'
        '  "Private :: Do Not Upload",\n'
        ']\n'
    )

    _TOML_WITHOUT_PRIVATE = (
        '[project]\n'
        'name = "pkg-b"\n'
        'version = "1.0"\n'
        'classifiers = [\n'
        '  "Development Status :: 3 - Alpha",\n'
        '  "License :: OSI Approved :: Apache Software License",\n'
        ']\n'
    )

    def _make_pkg(
        self,
        tmp_path: Path,
        name: str,
        toml_content: str,
        *,
        is_publishable: bool = True,
    ) -> Package:
        """Make pkg."""
        pkg_dir = tmp_path / name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(toml_content, encoding='utf-8')
        return Package(
            name=name,
            version='1.0',
            path=pkg_dir,
            manifest_path=pyproject,
            is_publishable=is_publishable,
        )

    def test_add_classifier_when_excluded(self, tmp_path: Path) -> None:
        """Excluded package missing classifier gets it added."""
        pkg = self._make_pkg(tmp_path, 'pkg-b', self._TOML_WITHOUT_PRIVATE, is_publishable=True)
        changes = fix_publish_classifiers([pkg], ['pkg-b'])

        assert len(changes) == 1
        assert 'added' in changes[0]
        content = pkg.manifest_path.read_text(encoding='utf-8')
        assert 'Private :: Do Not Upload' in content

    def test_remove_classifier_when_not_excluded(self, tmp_path: Path) -> None:
        """Non-excluded package with classifier gets it removed."""
        pkg = self._make_pkg(tmp_path, 'pkg-a', self._TOML_WITH_PRIVATE, is_publishable=False)
        changes = fix_publish_classifiers([pkg], [])

        assert len(changes) == 1
        assert 'removed' in changes[0]
        content = pkg.manifest_path.read_text(encoding='utf-8')
        assert 'Private :: Do Not Upload' not in content

    def test_no_change_when_consistent(self, tmp_path: Path) -> None:
        """Already-consistent packages produce no changes."""
        pkg_excluded = self._make_pkg(
            tmp_path,
            'pkg-a',
            self._TOML_WITH_PRIVATE,
            is_publishable=False,
        )
        pkg_published = self._make_pkg(
            tmp_path,
            'pkg-b',
            self._TOML_WITHOUT_PRIVATE,
            is_publishable=True,
        )
        changes = fix_publish_classifiers([pkg_excluded, pkg_published], ['pkg-a'])

        assert changes == []

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """Dry run reports changes but does not modify files."""
        pkg = self._make_pkg(tmp_path, 'pkg-b', self._TOML_WITHOUT_PRIVATE, is_publishable=True)
        original = pkg.manifest_path.read_text(encoding='utf-8')

        changes = fix_publish_classifiers([pkg], ['pkg-b'], dry_run=True)

        assert len(changes) == 1
        assert 'added' in changes[0]
        after = pkg.manifest_path.read_text(encoding='utf-8')
        assert after == original

    def test_glob_pattern_matching(self, tmp_path: Path) -> None:
        """Glob patterns in exclude_publish are matched correctly."""
        pkg = self._make_pkg(tmp_path, 'sample-hello', self._TOML_WITHOUT_PRIVATE, is_publishable=True)
        changes = fix_publish_classifiers([pkg], ['sample-*'])

        assert len(changes) == 1
        assert 'added' in changes[0]

    def test_preserves_toml_formatting(self, tmp_path: Path) -> None:
        """Tomlkit preserves comments and formatting when adding classifier."""
        toml_with_comment = (
            '# My package config\n'
            '[project]\n'
            'name = "pkg-c"\n'
            'version = "1.0"\n'
            'classifiers = [\n'
            '  "Development Status :: 3 - Alpha",\n'
            ']\n'
        )
        pkg = self._make_pkg(tmp_path, 'pkg-c', toml_with_comment, is_publishable=True)
        fix_publish_classifiers([pkg], ['pkg-c'])

        content = pkg.manifest_path.read_text(encoding='utf-8')
        assert '# My package config' in content
        assert 'Private :: Do Not Upload' in content

    def test_multiple_packages_mixed(self, tmp_path: Path) -> None:
        """Handles a mix of add/remove/no-change in one call."""
        pkg_remove = self._make_pkg(
            tmp_path,
            'pkg-remove',
            self._TOML_WITH_PRIVATE,
            is_publishable=False,
        )
        pkg_add = self._make_pkg(
            tmp_path,
            'pkg-add',
            self._TOML_WITHOUT_PRIVATE,
            is_publishable=True,
        )
        pkg_ok = self._make_pkg(
            tmp_path,
            'pkg-ok',
            self._TOML_WITHOUT_PRIVATE,
            is_publishable=True,
        )
        changes = fix_publish_classifiers(
            [pkg_remove, pkg_add, pkg_ok],
            ['pkg-add'],  # only pkg-add should be excluded
        )

        assert len(changes) == 2
        actions = {c.split(':')[0] for c in changes}
        assert 'pkg-remove' in actions
        assert 'pkg-add' in actions


class TestFixReadmeField:
    """Tests for fix_readme_field()."""

    def test_adds_readme_field(self, tmp_path: Path) -> None:
        """Adds readme = "README.md" when missing but file exists."""
        pkg_dir = tmp_path / 'plugins' / 'foo'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'README.md').write_text('# Foo', encoding='utf-8')
        toml = '[project]\nname = "foo"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='foo',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_readme_field([pkg])
        assert len(changes) == 1
        assert 'readme' in changes[0]
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'readme = "README.md"' in content

    def test_skips_when_readme_already_set(self, tmp_path: Path) -> None:
        """No change when readme is already declared."""
        pkg_dir = tmp_path / 'plugins' / 'bar'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'README.md').write_text('# Bar', encoding='utf-8')
        toml = '[project]\nname = "bar"\nversion = "1.0"\nreadme = "README.md"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='bar',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_readme_field([pkg])
        assert len(changes) == 0

    def test_skips_when_no_readme_file(self, tmp_path: Path) -> None:
        """No change when README.md doesn't exist on disk."""
        pkg_dir = tmp_path / 'plugins' / 'baz'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "baz"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='baz',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_readme_field([pkg])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports changes without writing."""
        pkg_dir = tmp_path / 'plugins' / 'dry'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'README.md').write_text('# Dry', encoding='utf-8')
        toml = '[project]\nname = "dry"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='dry',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_readme_field([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'readme' not in content


class TestFixChangelogUrl:
    """Tests for fix_changelog_url()."""

    def test_adds_changelog_url(self, tmp_path: Path) -> None:
        """Adds Changelog URL when missing."""
        pkg_dir = tmp_path / 'plugins' / 'foo'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "foo"\nversion = "1.0"\n\n[project.urls]\nHomepage = "https://example.com"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='foo',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_changelog_url([pkg], repo_owner='myorg', repo_name='myrepo')
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'Changelog' in content
        assert 'myorg/myrepo' in content

    def test_skips_when_changelog_exists(self, tmp_path: Path) -> None:
        """No change when Changelog URL already present."""
        pkg_dir = tmp_path / 'plugins' / 'bar'
        pkg_dir.mkdir(parents=True)
        toml = (
            '[project]\nname = "bar"\nversion = "1.0"\n\n'
            '[project.urls]\nChangelog = "https://example.com/CHANGELOG.md"\n'
        )
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='bar',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_changelog_url([pkg], repo_owner='myorg', repo_name='myrepo')
        assert len(changes) == 0

    def test_creates_urls_section(self, tmp_path: Path) -> None:
        """Creates [project.urls] when it doesn't exist."""
        pkg_dir = tmp_path / 'plugins' / 'new'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "new"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')

        pkg = Package(
            name='new',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_changelog_url([pkg], repo_owner='org', repo_name='repo')
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'Changelog' in content


class TestFixNamespaceInit:
    """Tests for fix_namespace_init()."""

    def test_deletes_namespace_init(self, tmp_path: Path) -> None:
        """Deletes __init__.py in namespace directories."""
        plugin_dir = tmp_path / 'plugins' / 'myplugin'
        ns_dir = plugin_dir / 'src' / 'myns'
        ns_dir.mkdir(parents=True)
        init_file = ns_dir / '__init__.py'
        init_file.write_text('# bad', encoding='utf-8')

        pkg = Package(
            name='myplugin',
            version='1.0',
            path=plugin_dir,
            manifest_path=plugin_dir / 'pyproject.toml',
        )
        changes = fix_namespace_init([pkg], ['myns'], plugin_dirs=['plugins'])
        assert len(changes) == 1
        assert not init_file.exists()

    def test_skips_non_plugins(self, tmp_path: Path) -> None:
        """Non-plugin packages are not touched when plugin_dirs is set."""
        core_dir = tmp_path / 'packages' / 'core'
        ns_dir = core_dir / 'src' / 'myns'
        ns_dir.mkdir(parents=True)
        init_file = ns_dir / '__init__.py'
        init_file.write_text('', encoding='utf-8')

        pkg = Package(
            name='core',
            version='1.0',
            path=core_dir,
            manifest_path=core_dir / 'pyproject.toml',
        )
        changes = fix_namespace_init([pkg], ['myns'], plugin_dirs=['plugins'])
        assert len(changes) == 0
        assert init_file.exists()

    def test_empty_namespace_dirs(self) -> None:
        """No changes when namespace_dirs is empty."""
        changes = fix_namespace_init([], [])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't delete."""
        plugin_dir = tmp_path / 'plugins' / 'dry'
        ns_dir = plugin_dir / 'src' / 'myns'
        ns_dir.mkdir(parents=True)
        init_file = ns_dir / '__init__.py'
        init_file.write_text('', encoding='utf-8')

        pkg = Package(
            name='dry',
            version='1.0',
            path=plugin_dir,
            manifest_path=plugin_dir / 'pyproject.toml',
        )
        changes = fix_namespace_init([pkg], ['myns'], plugin_dirs=['plugins'], dry_run=True)
        assert len(changes) == 1
        assert init_file.exists()


class TestFixTypeMarkers:
    """Tests for fix_type_markers()."""

    def test_creates_py_typed(self, tmp_path: Path) -> None:
        """Creates py.typed in the first top-level package dir."""
        pkg_dir = tmp_path / 'packages' / 'mylib'
        src_pkg = pkg_dir / 'src' / 'mylib'
        src_pkg.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mylib"\nversion = "1.0"\n',
            encoding='utf-8',
        )

        pkg = Package(
            name='mylib',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_type_markers([pkg], library_dirs=['packages', 'plugins'])
        assert len(changes) == 1
        assert (src_pkg / 'py.typed').exists()

    def test_skips_when_py_typed_exists(self, tmp_path: Path) -> None:
        """No change when py.typed already exists."""
        pkg_dir = tmp_path / 'packages' / 'typed'
        src_pkg = pkg_dir / 'src' / 'typed'
        src_pkg.mkdir(parents=True)
        (src_pkg / 'py.typed').write_text('', encoding='utf-8')
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "typed"\nversion = "1.0"\n',
            encoding='utf-8',
        )

        pkg = Package(
            name='typed',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_type_markers([pkg], library_dirs=['packages', 'plugins'])
        assert len(changes) == 0

    def test_skips_non_library(self, tmp_path: Path) -> None:
        """Packages not under library_dirs are skipped when configured."""
        pkg_dir = tmp_path / 'samples' / 'demo'
        src_pkg = pkg_dir / 'src' / 'demo'
        src_pkg.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "demo"\nversion = "1.0"\n',
            encoding='utf-8',
        )

        pkg = Package(
            name='demo',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_type_markers([pkg], library_dirs=['packages', 'plugins'])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't create file."""
        pkg_dir = tmp_path / 'packages' / 'drylib'
        src_pkg = pkg_dir / 'src' / 'drylib'
        src_pkg.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drylib"\nversion = "1.0"\n',
            encoding='utf-8',
        )

        pkg = Package(
            name='drylib',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_type_markers([pkg], dry_run=True)
        assert len(changes) == 1
        assert not (src_pkg / 'py.typed').exists()


class TestFixStaleArtifacts:
    """Tests for fix_stale_artifacts()."""

    def test_deletes_bak_files(self, tmp_path: Path) -> None:
        """Deletes .bak files."""
        pkg_dir = tmp_path / 'packages' / 'pkg'
        pkg_dir.mkdir(parents=True)
        bak = pkg_dir / 'pyproject.toml.bak'
        bak.write_text('old', encoding='utf-8')

        pkg = Package(
            name='pkg',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_stale_artifacts([pkg])
        assert len(changes) == 1
        assert not bak.exists()

    def test_deletes_dist_dir(self, tmp_path: Path) -> None:
        """Deletes dist/ directories."""
        pkg_dir = tmp_path / 'packages' / 'pkg'
        dist_dir = pkg_dir / 'dist'
        dist_dir.mkdir(parents=True)
        (dist_dir / 'pkg-1.0.tar.gz').write_text('', encoding='utf-8')

        pkg = Package(
            name='pkg',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_stale_artifacts([pkg])
        assert len(changes) == 1
        assert not dist_dir.exists()

    def test_no_artifacts(self, tmp_path: Path) -> None:
        """No changes when no stale artifacts exist."""
        pkg_dir = tmp_path / 'packages' / 'clean'
        pkg_dir.mkdir(parents=True)

        pkg = Package(
            name='clean',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_stale_artifacts([pkg])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't delete."""
        pkg_dir = tmp_path / 'packages' / 'dry'
        pkg_dir.mkdir(parents=True)
        bak = pkg_dir / 'foo.bak'
        bak.write_text('old', encoding='utf-8')

        pkg = Package(
            name='dry',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_stale_artifacts([pkg], dry_run=True)
        assert len(changes) == 1
        assert bak.exists()


class TestFixMissingReadme:
    """Tests for fix_missing_readme()."""

    def test_creates_readme(self, tmp_path: Path) -> None:
        """Creates README.md with package name heading."""
        pkg_dir = tmp_path / 'packages' / 'noreadme'
        pkg_dir.mkdir(parents=True)

        pkg = Package(
            name='noreadme',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_readme([pkg])
        assert len(changes) == 1
        readme = pkg_dir / 'README.md'
        assert readme.exists()
        assert '# noreadme' in readme.read_text(encoding='utf-8')

    def test_skips_existing_readme(self, tmp_path: Path) -> None:
        """No change when README.md already exists."""
        pkg_dir = tmp_path / 'packages' / 'hasreadme'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'README.md').write_text('# Existing', encoding='utf-8')

        pkg = Package(
            name='hasreadme',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_readme([pkg])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't create file."""
        pkg_dir = tmp_path / 'packages' / 'dry'
        pkg_dir.mkdir(parents=True)

        pkg = Package(
            name='dry',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_readme([pkg], dry_run=True)
        assert len(changes) == 1
        assert not (pkg_dir / 'README.md').exists()


class TestFixMissingLicense:
    """Tests for fix_missing_license()."""

    def test_creates_license(self, tmp_path: Path) -> None:
        """Creates LICENSE from bundled releasekit LICENSE."""
        pkg_dir = tmp_path / 'packages' / 'nolicense'
        pkg_dir.mkdir(parents=True)

        pkg = Package(
            name='nolicense',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_license([pkg])
        assert len(changes) == 1
        license_file = pkg_dir / 'LICENSE'
        assert license_file.exists()
        assert 'Apache' in license_file.read_text(encoding='utf-8')

    def test_skips_existing_license(self, tmp_path: Path) -> None:
        """No change when LICENSE already exists."""
        pkg_dir = tmp_path / 'packages' / 'haslicense'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'LICENSE').write_text('MIT', encoding='utf-8')

        pkg = Package(
            name='haslicense',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_license([pkg])
        assert len(changes) == 0

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't create file."""
        pkg_dir = tmp_path / 'packages' / 'dry'
        pkg_dir.mkdir(parents=True)

        pkg = Package(
            name='dry',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )
        changes = fix_missing_license([pkg], dry_run=True)
        assert len(changes) == 1
        assert not (pkg_dir / 'LICENSE').exists()


class TestTestFilenameCollisions:
    """Tests for the test_filename_collisions check (PythonCheckBackend)."""

    def test_no_collision_passes(self, tmp_path: Path) -> None:
        """Unique test filenames across packages produce a pass."""
        pkg_a = tmp_path / 'packages' / 'alpha'
        (pkg_a / 'tests').mkdir(parents=True)
        (pkg_a / 'tests' / 'alpha_test.py').write_text('', encoding='utf-8')

        pkg_b = tmp_path / 'packages' / 'beta'
        (pkg_b / 'tests').mkdir(parents=True)
        (pkg_b / 'tests' / 'beta_test.py').write_text('', encoding='utf-8')

        packages = [
            Package(name='alpha', version='1.0', path=pkg_a, manifest_path=pkg_a / 'pyproject.toml'),
            Package(name='beta', version='1.0', path=pkg_b, manifest_path=pkg_b / 'pyproject.toml'),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions(packages, result)
        assert 'test_filename_collisions' in result.passed

    def test_collision_warns(self, tmp_path: Path) -> None:
        """Identical test filenames across packages produce a warning."""
        pkg_a = tmp_path / 'packages' / 'alpha'
        (pkg_a / 'tests').mkdir(parents=True)
        (pkg_a / 'tests' / 'utils_test.py').write_text('', encoding='utf-8')

        pkg_b = tmp_path / 'packages' / 'beta'
        (pkg_b / 'tests').mkdir(parents=True)
        (pkg_b / 'tests' / 'utils_test.py').write_text('', encoding='utf-8')

        packages = [
            Package(name='alpha', version='1.0', path=pkg_a, manifest_path=pkg_a / 'pyproject.toml'),
            Package(name='beta', version='1.0', path=pkg_b, manifest_path=pkg_b / 'pyproject.toml'),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions(packages, result)
        assert 'test_filename_collisions' in result.warnings
        msg = result.warning_messages['test_filename_collisions']
        assert 'utils_test.py' in msg
        assert 'alpha' in msg
        assert 'beta' in msg

    def test_no_tests_dir_passes(self, tmp_path: Path) -> None:
        """Packages without tests/ directories don't cause issues."""
        pkg_a = tmp_path / 'packages' / 'alpha'
        pkg_a.mkdir(parents=True)

        packages = [
            Package(name='alpha', version='1.0', path=pkg_a, manifest_path=pkg_a / 'pyproject.toml'),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions(packages, result)
        assert 'test_filename_collisions' in result.passed

    def test_test_prefix_collision(self, tmp_path: Path) -> None:
        """Files matching test_*.py pattern are also detected."""
        pkg_a = tmp_path / 'packages' / 'alpha'
        (pkg_a / 'tests').mkdir(parents=True)
        (pkg_a / 'tests' / 'test_helpers.py').write_text('', encoding='utf-8')

        pkg_b = tmp_path / 'packages' / 'beta'
        (pkg_b / 'tests').mkdir(parents=True)
        (pkg_b / 'tests' / 'test_helpers.py').write_text('', encoding='utf-8')

        packages = [
            Package(name='alpha', version='1.0', path=pkg_a, manifest_path=pkg_a / 'pyproject.toml'),
            Package(name='beta', version='1.0', path=pkg_b, manifest_path=pkg_b / 'pyproject.toml'),
        ]
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions(packages, result)
        assert 'test_filename_collisions' in result.warnings


# Helper to create a minimal publishable package for new check tests.


def _pub_pkg(
    tmp_path: Path,
    name: str,
    *,
    pyproject_extra: str = '',
    version: str = '1.0.0',
) -> Package:
    """Create a minimal publishable package directory and return a Package."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    project_section = (
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        f'[project]\nname = "{name}"\nversion = "{version}"\n'
        'requires-python = ">=3.10"\n'
        'readme = "README.md"\n'
        'description = "test"\n'
        'license = {text = "Apache-2.0"}\n'
        'authors = [{name = "Test"}]\n'
        'classifiers = ["License :: OSI Approved :: Apache Software License", "Typing :: Typed"]\n'
        'keywords = ["python"]\n'
    )
    # Only append default [project.urls] if pyproject_extra doesn't define its own.
    if '[project.urls]' not in pyproject_extra:
        urls_section = (
            '\n[project.urls]\n'
            'Changelog = "https://github.com/test/test/blob/main/CHANGELOG.md"\n'
            'Homepage = "https://github.com/test/test"\n'
            'Repository = "https://github.com/test/test"\n'
            '"Bug Tracker" = "https://github.com/test/test/issues"\n'
        )
    else:
        urls_section = ''
    # Insert pyproject_extra between [project] keys and [project.urls]
    # so that extra keys like `dependencies = [...]` stay under [project].
    content = project_section + pyproject_extra + urls_section
    (pkg_dir / 'pyproject.toml').write_text(content, encoding='utf-8')
    (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
    (pkg_dir / 'README.md').write_text(f'# {name}\n', encoding='utf-8')
    return Package(
        name=name,
        version=version,
        path=pkg_dir,
        manifest_path=pkg_dir / 'pyproject.toml',
    )


class TestBuildSystem:
    """Tests for check_build_system."""

    def test_passes_with_build_system(self, tmp_path: Path) -> None:
        """Valid [build-system] passes."""
        pkg = _pub_pkg(tmp_path, 'good')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)
        assert 'build_system' in result.passed

    def test_fails_without_build_system(self, tmp_path: Path) -> None:
        """Missing [build-system] fails."""
        pkg_dir = tmp_path / 'bad'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "bad"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='bad', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)
        assert 'build_system' in result.failed

    def test_fails_without_build_backend(self, tmp_path: Path) -> None:
        """Missing build-backend key fails."""
        pkg_dir = tmp_path / 'nobackend'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\n\n[project]\nname = "nobackend"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='nobackend', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)
        assert 'build_system' in result.failed


class TestVersionField:
    """Tests for check_version_field."""

    def test_passes_with_version(self, tmp_path: Path) -> None:
        """Explicit version passes."""
        pkg = _pub_pkg(tmp_path, 'versioned')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_field([pkg], result)
        assert 'version_field' in result.passed

    def test_warns_without_version(self, tmp_path: Path) -> None:
        """Missing version warns."""
        pkg_dir = tmp_path / 'noversion'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "noversion"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='noversion', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_field([pkg], result)
        assert 'version_field' in result.warnings

    def test_passes_with_dynamic_version(self, tmp_path: Path) -> None:
        """Dynamic version passes."""
        pkg_dir = tmp_path / 'dynver'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "dynver"\ndynamic = ["version"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='dynver', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_field([pkg], result)
        assert 'version_field' in result.passed


class TestDuplicateDependencies:
    """Tests for check_duplicate_dependencies."""

    def test_passes_no_dupes(self, tmp_path: Path) -> None:
        """Unique dependencies pass."""
        pkg = _pub_pkg(tmp_path, 'clean', pyproject_extra='dependencies = ["requests>=2.0", "httpx"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([pkg], result)
        assert 'duplicate_dependencies' in result.passed

    def test_warns_on_dupes(self, tmp_path: Path) -> None:
        """Duplicate dependency names warn."""
        pkg = _pub_pkg(tmp_path, 'duped', pyproject_extra='dependencies = ["requests>=2.0", "requests<3.0"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([pkg], result)
        assert 'duplicate_dependencies' in result.warnings

    def test_normalizes_names(self, tmp_path: Path) -> None:
        """Hyphen/underscore normalization detects dupes."""
        pkg = _pub_pkg(tmp_path, 'norm', pyproject_extra='dependencies = ["my-pkg>=1", "my_pkg<2"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([pkg], result)
        assert 'duplicate_dependencies' in result.warnings


class TestPinnedDepsInLibraries:
    """Tests for check_pinned_deps_in_libraries."""

    def test_passes_no_pinned(self, tmp_path: Path) -> None:
        """Non-pinned deps pass."""
        pkg = _pub_pkg(tmp_path, 'flex', pyproject_extra='dependencies = ["requests>=2.0"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_pinned_deps_in_libraries([pkg], result)
        assert 'pinned_deps_in_libraries' in result.passed

    def test_warns_on_pinned(self, tmp_path: Path) -> None:
        """Pinned == deps in libraries warn."""
        pkg = _pub_pkg(tmp_path, 'pinned', pyproject_extra='dependencies = ["requests==2.28.0"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_pinned_deps_in_libraries([pkg], result)
        assert 'pinned_deps_in_libraries' in result.warnings


class TestRequiresPython:
    """Tests for check_requires_python."""

    def test_passes_with_requires_python(self, tmp_path: Path) -> None:
        """Present requires-python passes."""
        pkg = _pub_pkg(tmp_path, 'pyver')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_requires_python([pkg], result)
        assert 'requires_python' in result.passed

    def test_warns_without_requires_python(self, tmp_path: Path) -> None:
        """Missing requires-python warns."""
        pkg_dir = tmp_path / 'nopyver'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "nopyver"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='nopyver', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_requires_python([pkg], result)
        assert 'requires_python' in result.warnings


class TestReadmeContentType:
    """Tests for check_readme_content_type."""

    def test_passes_simple_readme(self, tmp_path: Path) -> None:
        """Simple string readme passes."""
        pkg = _pub_pkg(tmp_path, 'simple')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_content_type([pkg], result)
        assert 'readme_content_type' in result.passed

    def test_warns_md_with_rst_content_type(self, tmp_path: Path) -> None:
        """.md file with text/x-rst content-type warns."""
        pkg_dir = tmp_path / 'mismatch'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "mismatch"\nversion = "1.0"\n\n'
            '[project.readme]\nfile = "README.md"\ncontent-type = "text/x-rst"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='mismatch', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_content_type([pkg], result)
        assert 'readme_content_type' in result.warnings


class TestVersionPep440:
    """Tests for check_version_pep440."""

    def test_passes_valid_version(self, tmp_path: Path) -> None:
        """Standard x.y.z version passes."""
        pkg = _pub_pkg(tmp_path, 'valid', version='1.2.3')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)
        assert 'version_pep440' in result.passed

    def test_passes_prerelease(self, tmp_path: Path) -> None:
        """PEP 440 prerelease version passes."""
        pkg = _pub_pkg(tmp_path, 'pre', version='1.0.0a1')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)
        assert 'version_pep440' in result.passed

    def test_fails_invalid_version(self, tmp_path: Path) -> None:
        """Non-PEP 440 version fails."""
        pkg = _pub_pkg(tmp_path, 'bad', version='v1.2.3-beta')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)
        assert 'version_pep440' in result.failed


class TestPlaceholderUrls:
    """Tests for check_placeholder_urls."""

    def test_passes_real_urls(self, tmp_path: Path) -> None:
        """Real URLs pass."""
        pkg = _pub_pkg(
            tmp_path,
            'realurls',
            pyproject_extra='\n[project.urls]\nHomepage = "https://github.com/org/repo"\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_placeholder_urls([pkg], result)
        assert 'placeholder_urls' in result.passed

    def test_warns_example_com(self, tmp_path: Path) -> None:
        """example.com URL warns."""
        pkg = _pub_pkg(
            tmp_path,
            'placeholder',
            pyproject_extra='\n[project.urls]\nHomepage = "https://example.com"\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_placeholder_urls([pkg], result)
        assert 'placeholder_urls' in result.warnings

    def test_warns_empty_url(self, tmp_path: Path) -> None:
        """Empty URL warns."""
        pkg = _pub_pkg(
            tmp_path,
            'emptyurl',
            pyproject_extra='\n[project.urls]\nHomepage = ""\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_placeholder_urls([pkg], result)
        assert 'placeholder_urls' in result.warnings


class TestLegacySetupFiles:
    """Tests for check_legacy_setup_files."""

    def test_passes_no_legacy(self, tmp_path: Path) -> None:
        """No setup.py/cfg passes."""
        pkg = _pub_pkg(tmp_path, 'modern')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([pkg], result)
        assert 'legacy_setup_files' in result.passed

    def test_warns_setup_py(self, tmp_path: Path) -> None:
        """Leftover setup.py warns."""
        pkg = _pub_pkg(tmp_path, 'hassetuppy')
        (pkg.path / 'setup.py').write_text('', encoding='utf-8')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([pkg], result)
        assert 'legacy_setup_files' in result.warnings

    def test_warns_setup_cfg(self, tmp_path: Path) -> None:
        """Leftover setup.cfg warns."""
        pkg = _pub_pkg(tmp_path, 'hassetupcfg')
        (pkg.path / 'setup.cfg').write_text('', encoding='utf-8')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([pkg], result)
        assert 'legacy_setup_files' in result.warnings


class TestDeprecatedClassifiers:
    """Tests for check_deprecated_classifiers and fix_deprecated_classifiers."""

    def test_passes_no_deprecated(self, tmp_path: Path) -> None:
        """No deprecated classifiers passes."""
        pkg = _pub_pkg(tmp_path, 'cleanclf')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_deprecated_classifiers([pkg], result)
        assert 'deprecated_classifiers' in result.passed

    def test_warns_deprecated(self, tmp_path: Path) -> None:
        """Deprecated classifier warns."""
        deprecated_clf = next(iter(DEPRECATED_CLASSIFIERS))
        pkg_dir = tmp_path / 'depr'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            f'[project]\nname = "depr"\nversion = "1.0"\nclassifiers = ["{deprecated_clf}"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='depr', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_deprecated_classifiers([pkg], result)
        assert 'deprecated_classifiers' in result.warnings

    def test_fix_replaces_deprecated(self, tmp_path: Path) -> None:
        """Fixer replaces deprecated classifier with replacement."""
        deprecated_clf = 'Natural Language :: Ukranian'
        replacement = DEPRECATED_CLASSIFIERS[deprecated_clf]
        pkg_dir = tmp_path / 'fixme'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            f'[project]\nname = "fixme"\nversion = "1.0"\nclassifiers = ["{deprecated_clf}"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='fixme', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_deprecated_classifiers([pkg])
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert replacement in content
        assert deprecated_clf not in content

    def test_fix_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        deprecated_clf = 'Natural Language :: Ukranian'
        pkg_dir = tmp_path / 'drydepr'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            f'[project]\nname = "drydepr"\nversion = "1.0"\nclassifiers = ["{deprecated_clf}"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='drydepr', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_deprecated_classifiers([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert deprecated_clf in content


class TestLicenseClassifierMismatch:
    """Tests for check_license_classifier_mismatch."""

    def test_passes_matching_license(self, tmp_path: Path) -> None:
        """Matching license classifier and file passes."""
        pkg = _pub_pkg(tmp_path, 'licmatch')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_license_classifier_mismatch([pkg], result)
        assert 'license_classifier_mismatch' in result.passed

    def test_warns_mismatch(self, tmp_path: Path) -> None:
        """Apache LICENSE with MIT classifier warns."""
        pkg_dir = tmp_path / 'licmis'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "licmis"\nversion = "1.0"\nclassifiers = ["License :: OSI Approved :: MIT License"]\n',
            encoding='utf-8',
        )
        # LICENSE says Apache but classifier says MIT.
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='licmis', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_license_classifier_mismatch([pkg], result)
        assert 'license_classifier_mismatch' in result.warnings


class TestUnreachableExtras:
    """Tests for check_unreachable_extras."""

    def test_passes_valid_extras(self, tmp_path: Path) -> None:
        """Valid optional-dependencies pass."""
        pkg = _pub_pkg(
            tmp_path,
            'validextras',
            pyproject_extra='\n[project.optional-dependencies]\ndev = ["pytest>=7.0"]\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_unreachable_extras([pkg], result)
        assert 'unreachable_extras' in result.passed

    def test_passes_empty_extras(self, tmp_path: Path) -> None:
        """No optional-dependencies passes."""
        pkg = _pub_pkg(tmp_path, 'noextras')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_unreachable_extras([pkg], result)
        assert 'unreachable_extras' in result.passed


class TestFixDuplicateDependencies:
    """Tests for fix_duplicate_dependencies."""

    def test_removes_exact_dupes(self, tmp_path: Path) -> None:
        """Exact duplicate dep names are removed, keeping the first."""
        pkg_dir = tmp_path / 'dupes'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dupes"\nversion = "1.0"\ndependencies = ["requests>=2.0", "requests<3.0"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='dupes', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_duplicate_dependencies([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        deps = list(doc['project']['dependencies'])
        assert deps == ['requests>=2.0']

    def test_normalizes_names(self, tmp_path: Path) -> None:
        """Hyphen/underscore/dot variants are treated as duplicates."""
        pkg_dir = tmp_path / 'norm'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "norm"\nversion = "1.0"\ndependencies = ["my-pkg>=1", "my_pkg<2"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='norm', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_duplicate_dependencies([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        deps = list(doc['project']['dependencies'])
        assert deps == ['my-pkg>=1']

    def test_no_dupes_no_changes(self, tmp_path: Path) -> None:
        """No duplicates means no changes."""
        pkg = _pub_pkg(tmp_path, 'nodupes', pyproject_extra='dependencies = ["requests", "httpx"]\n')
        changes = fix_duplicate_dependencies([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'drydupes'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drydupes"\nversion = "1.0"\ndependencies = ["requests>=2", "requests<3"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='drydupes', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_duplicate_dependencies([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'requests<3' in content


class TestFixRequiresPython:
    """Tests for fix_requires_python."""

    def test_adds_default(self, tmp_path: Path) -> None:
        """Missing requires-python gets the default value."""
        pkg_dir = tmp_path / 'nopyver'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nopyver"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        pkg = Package(name='nopyver', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_requires_python([pkg])
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert '>=3.10' in content

    def test_infers_from_classifiers(self, tmp_path: Path) -> None:
        """Infers minimum version from Python classifiers."""
        pkg_dir = tmp_path / 'infer'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "infer"\nversion = "1.0"\n'
            'classifiers = [\n'
            '  "Programming Language :: Python :: 3.11",\n'
            '  "Programming Language :: Python :: 3.12",\n'
            ']\n',
            encoding='utf-8',
        )
        pkg = Package(name='infer', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_requires_python([pkg])
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert '>=3.11' in content

    def test_skips_existing(self, tmp_path: Path) -> None:
        """Packages that already have requires-python are skipped."""
        pkg = _pub_pkg(tmp_path, 'haspyver')
        changes = fix_requires_python([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'drypyver'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drypyver"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        pkg = Package(name='drypyver', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_requires_python([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'requires-python' not in content


class TestFixBuildSystem:
    """Tests for fix_build_system."""

    def test_adds_build_system(self, tmp_path: Path) -> None:
        """Missing [build-system] gets added with hatchling default."""
        pkg_dir = tmp_path / 'nobs'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nobs"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        pkg = Package(name='nobs', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_build_system([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert doc['build-system']['build-backend'] == 'hatchling.build'
        assert 'hatchling' in doc['build-system']['requires']

    def test_adds_build_backend_only(self, tmp_path: Path) -> None:
        """[build-system] exists but missing build-backend gets it added."""
        pkg_dir = tmp_path / 'nobackend'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\n\n[project]\nname = "nobackend"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        pkg = Package(name='nobackend', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_build_system([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert doc['build-system']['build-backend'] == 'hatchling.build'

    def test_skips_complete(self, tmp_path: Path) -> None:
        """Already-complete [build-system] is skipped."""
        pkg = _pub_pkg(tmp_path, 'complete')
        changes = fix_build_system([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'drybs'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drybs"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        pkg = Package(name='drybs', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_build_system([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'build-system' not in content


class TestFixVersionField:
    """Tests for fix_version_field."""

    def test_adds_dynamic_version(self, tmp_path: Path) -> None:
        """Missing version gets dynamic = ["version"] added."""
        pkg_dir = tmp_path / 'nover'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nover"\n',
            encoding='utf-8',
        )
        pkg = Package(name='nover', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_version_field([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'version' in doc['project']['dynamic']

    def test_appends_to_existing_dynamic(self, tmp_path: Path) -> None:
        """Appends "version" to an existing dynamic list."""
        pkg_dir = tmp_path / 'dynexist'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dynexist"\ndynamic = ["readme"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='dynexist', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_version_field([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'version' in doc['project']['dynamic']
        assert 'readme' in doc['project']['dynamic']

    def test_skips_with_version(self, tmp_path: Path) -> None:
        """Package with explicit version is skipped."""
        pkg = _pub_pkg(tmp_path, 'hasver')
        changes = fix_version_field([pkg])
        assert changes == []

    def test_skips_already_dynamic(self, tmp_path: Path) -> None:
        """Package with version already in dynamic is skipped."""
        pkg_dir = tmp_path / 'alreadydyn'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "alreadydyn"\ndynamic = ["version"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='alreadydyn', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_version_field([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'dryvf'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dryvf"\n',
            encoding='utf-8',
        )
        pkg = Package(name='dryvf', version='', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_version_field([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'dynamic' not in content


class TestFixReadmeContentType:
    """Tests for fix_readme_content_type."""

    def test_fixes_md_with_rst_ct(self, tmp_path: Path) -> None:
        """.md file with text/x-rst gets corrected to text/markdown."""
        pkg_dir = tmp_path / 'fixct'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "fixct"\nversion = "1.0"\n\n'
            '[project.readme]\nfile = "README.md"\ncontent-type = "text/x-rst"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='fixct', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_readme_content_type([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert doc['project']['readme']['content-type'] == 'text/markdown'

    def test_fixes_rst_with_md_ct(self, tmp_path: Path) -> None:
        """.rst file with text/markdown gets corrected to text/x-rst."""
        pkg_dir = tmp_path / 'fixrst'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "fixrst"\nversion = "1.0"\n\n'
            '[project.readme]\nfile = "README.rst"\ncontent-type = "text/markdown"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'README.rst').write_text('', encoding='utf-8')
        pkg = Package(name='fixrst', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_readme_content_type([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert doc['project']['readme']['content-type'] == 'text/x-rst'

    def test_skips_correct(self, tmp_path: Path) -> None:
        """Matching content-type is skipped."""
        pkg_dir = tmp_path / 'correct'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "correct"\nversion = "1.0"\n\n'
            '[project.readme]\nfile = "README.md"\ncontent-type = "text/markdown"\n',
            encoding='utf-8',
        )
        pkg = Package(name='correct', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_readme_content_type([pkg])
        assert changes == []

    def test_skips_string_readme(self, tmp_path: Path) -> None:
        """Simple string readme (not a table) is skipped."""
        pkg = _pub_pkg(tmp_path, 'strreadme')
        changes = fix_readme_content_type([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'dryct'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dryct"\nversion = "1.0"\n\n'
            '[project.readme]\nfile = "README.md"\ncontent-type = "text/x-rst"\n',
            encoding='utf-8',
        )
        pkg = Package(name='dryct', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_readme_content_type([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'text/x-rst' in content


class TestFixPlaceholderUrls:
    """Tests for fix_placeholder_urls."""

    def test_removes_example_com(self, tmp_path: Path) -> None:
        """example.com URL is removed."""
        pkg_dir = tmp_path / 'phurl'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "phurl"\nversion = "1.0"\n\n'
            '[project.urls]\nHomepage = "https://example.com"\n'
            'Source = "https://github.com/org/repo"\n',
            encoding='utf-8',
        )
        pkg = Package(name='phurl', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_placeholder_urls([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'Homepage' not in doc['project']['urls']
        assert doc['project']['urls']['Source'] == 'https://github.com/org/repo'

    def test_removes_empty_url(self, tmp_path: Path) -> None:
        """Empty URL is removed."""
        pkg_dir = tmp_path / 'emptyurl'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "emptyurl"\nversion = "1.0"\n\n[project.urls]\nHomepage = ""\n',
            encoding='utf-8',
        )
        pkg = Package(name='emptyurl', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_placeholder_urls([pkg])
        assert len(changes) == 1

    def test_removes_todo_url(self, tmp_path: Path) -> None:
        """URL containing TODO is removed."""
        pkg_dir = tmp_path / 'todourl'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "todourl"\nversion = "1.0"\n\n[project.urls]\nHomepage = "TODO"\n',
            encoding='utf-8',
        )
        pkg = Package(name='todourl', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_placeholder_urls([pkg])
        assert len(changes) == 1

    def test_skips_real_urls(self, tmp_path: Path) -> None:
        """Real URLs are not removed."""
        pkg = _pub_pkg(
            tmp_path,
            'realurls2',
            pyproject_extra='\n[project.urls]\nHomepage = "https://github.com/org/repo"\n',
        )
        changes = fix_placeholder_urls([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'dryph'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dryph"\nversion = "1.0"\n\n[project.urls]\nHomepage = "https://example.com"\n',
            encoding='utf-8',
        )
        pkg = Package(name='dryph', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_placeholder_urls([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'example.com' in content


class TestFixLicenseClassifierMismatch:
    """Tests for fix_license_classifier_mismatch."""

    def test_fixes_mismatch(self, tmp_path: Path) -> None:
        """MIT classifier with Apache LICENSE gets corrected."""
        pkg_dir = tmp_path / 'licfix'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "licfix"\nversion = "1.0"\nclassifiers = ["License :: OSI Approved :: MIT License"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        pkg = Package(name='licfix', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_license_classifier_mismatch([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        clf = doc['project']['classifiers'][0]
        assert 'Apache' in clf

    def test_skips_matching(self, tmp_path: Path) -> None:
        """Matching license classifier is skipped."""
        pkg = _pub_pkg(tmp_path, 'licok')
        changes = fix_license_classifier_mismatch([pkg])
        assert changes == []

    def test_skips_no_license_file(self, tmp_path: Path) -> None:
        """Package without LICENSE file is skipped."""
        pkg_dir = tmp_path / 'nolic'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nolic"\nversion = "1.0"\nclassifiers = ["License :: OSI Approved :: MIT License"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='nolic', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_license_classifier_mismatch([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'drylicfix'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drylicfix"\nversion = "1.0"\n'
            'classifiers = ["License :: OSI Approved :: MIT License"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        pkg = Package(name='drylicfix', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_license_classifier_mismatch([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'MIT' in content


class TestCheckSelfDependencies:
    """Tests for check_self_dependencies."""

    def test_passes_no_self_dep(self, tmp_path: Path) -> None:
        """Package without self-dependency passes."""
        pkg = _pub_pkg(tmp_path, 'clean-pkg', pyproject_extra='dependencies = ["requests"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([pkg], result)
        assert 'self_dependencies' in result.passed

    def test_warns_self_dep(self, tmp_path: Path) -> None:
        """Package listing itself warns."""
        pkg = _pub_pkg(tmp_path, 'selfref', pyproject_extra='dependencies = ["selfref>=1.0"]\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([pkg], result)
        assert 'self_dependencies' in result.warnings

    def test_normalizes_name(self, tmp_path: Path) -> None:
        """Hyphen/underscore variants are detected as self-deps."""
        pkg_dir = tmp_path / 'my-pkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "my-pkg"\nversion = "1.0"\ndependencies = ["my_pkg>=1.0"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='my-pkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([pkg], result)
        assert 'self_dependencies' in result.warnings


class TestFixSelfDependencies:
    """Tests for fix_self_dependencies."""

    def test_removes_self_dep(self, tmp_path: Path) -> None:
        """Self-dependency is removed, other deps kept."""
        pkg_dir = tmp_path / 'selffix'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "selffix"\nversion = "1.0"\ndependencies = ["selffix>=1.0", "requests"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='selffix', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_self_dependencies([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        deps = list(doc['project']['dependencies'])
        assert deps == ['requests']

    def test_normalizes_name(self, tmp_path: Path) -> None:
        """Hyphen/underscore variants are removed."""
        pkg_dir = tmp_path / 'my-lib'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "my-lib"\nversion = "1.0"\ndependencies = ["my_lib>=1.0", "httpx"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='my-lib', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_self_dependencies([pkg])
        assert len(changes) == 1

        doc = _read_toml(pkg_dir / 'pyproject.toml')
        deps = list(doc['project']['dependencies'])
        assert deps == ['httpx']

    def test_no_self_dep_no_changes(self, tmp_path: Path) -> None:
        """No self-dep means no changes."""
        pkg = _pub_pkg(tmp_path, 'noself', pyproject_extra='dependencies = ["requests"]\n')
        changes = fix_self_dependencies([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports but doesn't modify."""
        pkg_dir = tmp_path / 'dryself'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dryself"\nversion = "1.0"\ndependencies = ["dryself>=1.0"]\n',
            encoding='utf-8',
        )
        pkg = Package(name='dryself', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_self_dependencies([pkg], dry_run=True)
        assert len(changes) == 1
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'dryself>=1.0' in content


class TestRunFixes:
    """Tests for PythonCheckBackend.run_fixes()."""

    def test_run_fixes_removes_self_dep(self, tmp_path: Path) -> None:
        """run_fixes dispatches to fix_self_dependencies."""
        pkg_dir = tmp_path / 'selfdep'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "selfdep"\nversion = "1.0"\n'
            'requires-python = ">=3.10"\n'
            'dependencies = ["selfdep>=1.0", "requests"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('# selfdep', encoding='utf-8')
        pkg = Package(name='selfdep', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('self-dep' in c for c in changes)

    def test_run_fixes_dry_run(self, tmp_path: Path) -> None:
        """Dry run propagates to all fixers."""
        pkg_dir = tmp_path / 'dryall'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "dryall"\nversion = "1.0"\ndependencies = ["dryall>=1.0"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('# dryall', encoding='utf-8')
        pkg = Package(name='dryall', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        changes = backend.run_fixes([pkg], dry_run=True)
        # Should report changes but not modify.
        assert len(changes) > 0
        content = (pkg_dir / 'pyproject.toml').read_text(encoding='utf-8')
        assert 'dryall>=1.0' in content

    def test_run_fixes_returns_empty_for_clean_pkg(self, tmp_path: Path) -> None:
        """Clean package produces no fix changes."""
        pkg = _pub_pkg(tmp_path, 'cleanpkg')
        backend = PythonCheckBackend()
        changes = backend.run_fixes([pkg])
        assert changes == []


class TestTypingClassifierCheck:
    """Tests for check_typing_classifier."""

    def test_passes_with_both_classifiers(self, tmp_path: Path) -> None:
        """Package with Typing :: Typed and License :: OSI Approved passes."""
        pkg = _pub_pkg(tmp_path, 'good')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_typing_classifier([pkg], result)
        assert 'typing_classifier' in result.passed

    def test_warns_missing_typing_typed(self, tmp_path: Path) -> None:
        """Package missing Typing :: Typed triggers warning."""
        pkg_dir = tmp_path / 'notyping'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "notyping"\nversion = "1.0"\n'
            'classifiers = ["License :: OSI Approved :: Apache Software License"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='notyping', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_typing_classifier([pkg], result)
        assert 'typing_classifier' in result.warnings

    def test_warns_missing_license_osi(self, tmp_path: Path) -> None:
        """Package missing License :: OSI Approved triggers warning."""
        pkg_dir = tmp_path / 'nolicense'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nolicense"\nversion = "1.0"\nclassifiers = ["Typing :: Typed"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='nolicense', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_typing_classifier([pkg], result)
        assert 'typing_classifier' in result.warnings

    def test_skips_unpublishable(self, tmp_path: Path) -> None:
        """Unpublishable packages are skipped."""
        pkg_dir = tmp_path / 'private'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "private"\nversion = "1.0"\nclassifiers = []\n',
            encoding='utf-8',
        )
        pkg = Package(
            name='private',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
            is_publishable=False,
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_typing_classifier([pkg], result)
        assert 'typing_classifier' in result.passed


class TestKeywordsAndUrlsCheck:
    """Tests for check_keywords_and_urls."""

    def test_passes_with_keywords_and_urls(self, tmp_path: Path) -> None:
        """Package with keywords and all standard URLs passes."""
        pkg = _pub_pkg(tmp_path, 'good')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_keywords_and_urls([pkg], result)
        assert 'keywords_and_urls' in result.passed

    def test_warns_missing_keywords(self, tmp_path: Path) -> None:
        """Package missing keywords triggers warning."""
        pkg_dir = tmp_path / 'nokw'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nokw"\nversion = "1.0"\n\n'
            '[project.urls]\n'
            'Homepage = "https://example.com"\n'
            'Repository = "https://example.com"\n'
            '"Bug Tracker" = "https://example.com/issues"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='nokw', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_keywords_and_urls([pkg], result)
        assert 'keywords_and_urls' in result.warnings

    def test_warns_missing_urls(self, tmp_path: Path) -> None:
        """Package missing [project.urls] triggers warning."""
        pkg_dir = tmp_path / 'nourls'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "nourls"\nversion = "1.0"\nkeywords = ["test"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='nourls', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_keywords_and_urls([pkg], result)
        assert 'keywords_and_urls' in result.warnings

    def test_warns_missing_standard_url_keys(self, tmp_path: Path) -> None:
        """Package with urls but missing Homepage/Repository triggers warning."""
        pkg_dir = tmp_path / 'partialurls'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "partialurls"\nversion = "1.0"\nkeywords = ["test"]\n\n'
            '[project.urls]\nChangelog = "https://example.com/CHANGELOG.md"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='partialurls', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_keywords_and_urls([pkg], result)
        assert 'keywords_and_urls' in result.warnings


class TestFixTypingClassifier:
    """Tests for fix_typing_classifier."""

    def test_adds_typing_typed(self, tmp_path: Path) -> None:
        """Adds Typing :: Typed when missing."""
        from releasekit.checks import fix_typing_classifier

        pkg_dir = tmp_path / 'mypkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nversion = "1.0"\n'
            'classifiers = ["License :: OSI Approved :: Apache Software License"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        pkg = Package(name='mypkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_typing_classifier([pkg])
        assert len(changes) == 1
        assert 'Typing :: Typed' in changes[0]
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'Typing :: Typed' in data['project']['classifiers']

    def test_adds_license_osi(self, tmp_path: Path) -> None:
        """Adds License :: OSI Approved when missing."""
        from releasekit.checks import fix_typing_classifier

        pkg_dir = tmp_path / 'mypkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nversion = "1.0"\nclassifiers = ["Typing :: Typed"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        pkg = Package(name='mypkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_typing_classifier([pkg])
        assert len(changes) == 1
        assert 'License :: OSI Approved' in changes[0]
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert any(c.startswith('License :: OSI Approved') for c in data['project']['classifiers'])

    def test_noop_when_both_present(self, tmp_path: Path) -> None:
        """No changes when both classifiers already present."""
        from releasekit.checks import fix_typing_classifier

        pkg = _pub_pkg(tmp_path, 'clean')
        changes = fix_typing_classifier([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports changes without writing."""
        from releasekit.checks import fix_typing_classifier

        pkg_dir = tmp_path / 'drpkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drpkg"\nversion = "1.0"\nclassifiers = []\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')
        pkg = Package(name='drpkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_typing_classifier([pkg], dry_run=True)
        assert len(changes) == 1
        # File should NOT be modified.
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'Typing :: Typed' not in data['project']['classifiers']


class TestFixKeywordsAndUrls:
    """Tests for fix_keywords_and_urls."""

    def test_adds_keywords(self, tmp_path: Path) -> None:
        """Adds keywords when missing."""
        from releasekit.checks import fix_keywords_and_urls

        pkg_dir = tmp_path / 'mypkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nversion = "1.0"\n\n'
            '[project.urls]\nHomepage = "https://example.com"\n'
            'Repository = "https://example.com"\n'
            '"Bug Tracker" = "https://example.com/issues"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='mypkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_keywords_and_urls([pkg])
        assert len(changes) == 1
        assert 'keywords' in changes[0]
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert data['project']['keywords'] == ['python']

    def test_adds_urls(self, tmp_path: Path) -> None:
        """Adds standard URLs when missing."""
        from releasekit.checks import fix_keywords_and_urls

        pkg_dir = tmp_path / 'mypkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nversion = "1.0"\nkeywords = ["test"]\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='mypkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_keywords_and_urls([pkg], repo_owner='firebase', repo_name='genkit')
        assert len(changes) == 1
        assert 'urls' in changes[0]
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'Homepage' in data['project']['urls']
        assert 'Repository' in data['project']['urls']
        assert 'Bug Tracker' in data['project']['urls']

    def test_noop_when_complete(self, tmp_path: Path) -> None:
        """No changes when keywords and all URLs already present."""
        from releasekit.checks import fix_keywords_and_urls

        pkg = _pub_pkg(tmp_path, 'clean')
        changes = fix_keywords_and_urls([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports changes without writing."""
        from releasekit.checks import fix_keywords_and_urls

        pkg_dir = tmp_path / 'drpkg'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "drpkg"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        (pkg_dir / 'LICENSE').write_text('Apache License', encoding='utf-8')
        (pkg_dir / 'README.md').write_text('', encoding='utf-8')
        pkg = Package(name='drpkg', version='1.0', path=pkg_dir, manifest_path=pkg_dir / 'pyproject.toml')
        changes = fix_keywords_and_urls([pkg], dry_run=True)
        assert len(changes) == 1
        # File should NOT be modified.
        data = _read_toml(pkg_dir / 'pyproject.toml')
        assert 'keywords' not in data['project']
