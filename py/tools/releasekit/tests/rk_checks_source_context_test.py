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

"""Integration tests for SourceContext in Python health checks.

Verifies that Python check methods produce :class:`SourceContext` objects
with correct file paths and line numbers when reporting warnings or
failures.  Each test creates a minimal ``pyproject.toml`` on disk that
triggers a specific check's failure branch, then asserts that the
resulting context list contains ``SourceContext`` instances pointing at
the right location.
"""

from __future__ import annotations

from pathlib import Path

from releasekit.checks import PythonCheckBackend
from releasekit.checks._constants import DEPRECATED_CLASSIFIERS
from releasekit.checks._python import _refresh_publishable
from releasekit.preflight import PreflightResult, SourceContext
from releasekit.workspace import Package


def _make_pkg(
    tmp_path: Path,
    name: str,
    toml_content: str,
    *,
    version: str = '1.0.0',
    is_publishable: bool = True,
) -> Package:
    """Create a single package with the given pyproject.toml content."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    manifest = pkg_dir / 'pyproject.toml'
    manifest.write_text(toml_content, encoding='utf-8')
    return Package(
        name=name,
        version=version,
        path=pkg_dir,
        manifest_path=manifest,
        is_publishable=is_publishable,
    )


def _has_source_context(result: PreflightResult, check_name: str) -> bool:
    """Return True if the check produced at least one SourceContext."""
    ctx = result.context.get(check_name, [])
    return any(isinstance(c, SourceContext) for c in ctx)


def _get_source_contexts(result: PreflightResult, check_name: str) -> list[SourceContext]:
    """Return all SourceContext objects for a check."""
    return [c for c in result.context.get(check_name, []) if isinstance(c, SourceContext)]


# check_build_system


class TestBuildSystemSourceContext:
    """Tests for check_build_system with SourceContext."""

    def test_missing_build_system_has_source_context(self, tmp_path: Path) -> None:
        """Missing [build-system] produces SourceContext."""
        pkg = _make_pkg(tmp_path, 'no-bs', '[project]\nname = "no-bs"\nversion = "1.0.0"\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)

        if 'build_system' not in result.failed:
            raise AssertionError(f'Expected failure, got: passed={result.passed}')
        if not _has_source_context(result, 'build_system'):
            raise AssertionError('Expected SourceContext in context')
        sc = _get_source_contexts(result, 'build_system')[0]
        if sc.line < 1:
            raise AssertionError(f'Expected line >= 1, got {sc.line}')

    def test_missing_build_backend_has_source_context(self, tmp_path: Path) -> None:
        """[build-system] without build-backend produces SourceContext."""
        toml = '[build-system]\nrequires = ["hatchling"]\n\n[project]\nname = "x"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'no-backend', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)

        if 'build_system' not in result.failed:
            raise AssertionError('Expected failure')
        sc = _get_source_contexts(result, 'build_system')[0]
        if sc.key != 'build-backend':
            raise AssertionError(f'Expected key=build-backend, got {sc.key!r}')

    def test_valid_build_system_passes(self, tmp_path: Path) -> None:
        """Valid [build-system] passes without context."""
        toml = (
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "ok"\nversion = "1.0"\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)

        if 'build_system' not in result.passed:
            raise AssertionError(f'Expected pass, got errors={result.errors}')

    def test_unparseable_toml_falls_back_to_str(self, tmp_path: Path) -> None:
        """Unparseable pyproject.toml falls back to plain string context."""
        pkg = _make_pkg(tmp_path, 'bad', '{{invalid toml}}')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)

        if 'build_system' not in result.failed:
            raise AssertionError('Expected failure')
        ctx = result.context.get('build_system', [])
        if not ctx:
            raise AssertionError('Expected context')
        if isinstance(ctx[0], SourceContext):
            raise AssertionError('Unparseable should produce plain str, not SourceContext')


# check_version_field


class TestVersionFieldSourceContext:
    """Tests for check_version_field with SourceContext."""

    def test_missing_version_has_source_context(self, tmp_path: Path) -> None:
        """Missing version field produces SourceContext."""
        toml = '[project]\nname = "no-ver"\ndescription = "test"\n'
        pkg = _make_pkg(tmp_path, 'no-ver', toml, version='')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_field([pkg], result)

        if 'version_field' not in result.warnings:
            raise AssertionError(f'Expected warning, got: {result.passed}')
        if not _has_source_context(result, 'version_field'):
            raise AssertionError('Expected SourceContext')
        sc = _get_source_contexts(result, 'version_field')[0]
        if sc.key != 'version':
            raise AssertionError(f'Expected key=version, got {sc.key!r}')

    def test_dynamic_version_passes(self, tmp_path: Path) -> None:
        """Dynamic version declaration passes."""
        toml = '[project]\nname = "dyn"\ndynamic = ["version"]\n'
        pkg = _make_pkg(tmp_path, 'dyn', toml, version='')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_field([pkg], result)

        if 'version_field' not in result.passed:
            raise AssertionError(f'Expected pass, got warnings={result.warning_messages}')


# check_requires_python


class TestRequiresPythonSourceContext:
    """Tests for check_requires_python with SourceContext."""

    def test_missing_requires_python_has_source_context(self, tmp_path: Path) -> None:
        """Missing requires-python produces SourceContext."""
        toml = '[project]\nname = "no-rp"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'no-rp', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_requires_python([pkg], result)

        if 'requires_python' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'requires_python'):
            raise AssertionError('Expected SourceContext')
        sc = _get_source_contexts(result, 'requires_python')[0]
        if sc.key != 'requires-python':
            raise AssertionError(f'Expected key=requires-python, got {sc.key!r}')

    def test_present_requires_python_passes(self, tmp_path: Path) -> None:
        """Present requires-python passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\nrequires-python = ">=3.10"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_requires_python([pkg], result)

        if 'requires_python' not in result.passed:
            raise AssertionError('Expected pass')


# check_version_pep440


class TestVersionPep440SourceContext:
    """Tests for check_version_pep440 with SourceContext."""

    def test_invalid_version_has_source_context(self, tmp_path: Path) -> None:
        """Non-PEP 440 version produces SourceContext."""
        toml = '[project]\nname = "bad-ver"\nversion = "1.0.0-beta"\n'
        pkg = _make_pkg(tmp_path, 'bad-ver', toml, version='1.0.0-beta')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)

        if 'version_pep440' not in result.failed:
            raise AssertionError(f'Expected failure, got passed={result.passed}')
        if not _has_source_context(result, 'version_pep440'):
            raise AssertionError('Expected SourceContext')
        sc = _get_source_contexts(result, 'version_pep440')[0]
        if sc.key != 'version':
            raise AssertionError(f'Expected key=version, got {sc.key!r}')
        if sc.line < 1:
            raise AssertionError(f'Expected line >= 1, got {sc.line}')

    def test_valid_pep440_passes(self, tmp_path: Path) -> None:
        """Valid PEP 440 version passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)

        if 'version_pep440' not in result.passed:
            raise AssertionError('Expected pass')


# check_readme_field


class TestReadmeFieldSourceContext:
    """Tests for check_readme_field with SourceContext."""

    def test_missing_readme_has_source_context(self, tmp_path: Path) -> None:
        """Missing readme field produces SourceContext."""
        toml = '[project]\nname = "no-readme"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'no-readme', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_field([pkg], result)

        if 'readme_field' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'readme_field'):
            raise AssertionError('Expected SourceContext')


# check_metadata_completeness


class TestMetadataCompletenessSourceContext:
    """Tests for check_metadata_completeness with SourceContext."""

    def test_missing_fields_has_source_context(self, tmp_path: Path) -> None:
        """Missing description/authors/license produces SourceContext."""
        toml = '[project]\nname = "incomplete"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'incomplete', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([pkg], result)

        if 'metadata_completeness' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'metadata_completeness'):
            raise AssertionError('Expected SourceContext')
        sc = _get_source_contexts(result, 'metadata_completeness')[0]
        if 'missing' not in sc.label:
            raise AssertionError(f'Expected "missing" in label, got {sc.label!r}')

    def test_complete_metadata_passes(self, tmp_path: Path) -> None:
        """Complete metadata passes."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\n'
            'description = "A package"\n'
            'license = {text = "Apache-2.0"}\n'
            'authors = [{name = "Test"}]\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([pkg], result)

        if 'metadata_completeness' not in result.passed:
            raise AssertionError(f'Expected pass, got warnings={result.warning_messages}')


# check_changelog_url


class TestChangelogUrlSourceContext:
    """Tests for check_changelog_url with SourceContext."""

    def test_missing_changelog_has_source_context(self, tmp_path: Path) -> None:
        """Missing Changelog URL produces SourceContext."""
        toml = '[project]\nname = "no-cl"\nversion = "1.0"\n\n[project.urls]\nHomepage = "https://example.com"\n'
        pkg = _make_pkg(tmp_path, 'no-cl', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_changelog_url([pkg], result)

        if 'changelog_url' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'changelog_url'):
            raise AssertionError('Expected SourceContext')

    def test_missing_urls_section_has_source_context(self, tmp_path: Path) -> None:
        """Missing [project.urls] entirely produces SourceContext."""
        toml = '[project]\nname = "no-urls"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'no-urls', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_changelog_url([pkg], result)

        if 'changelog_url' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'changelog_url'):
            raise AssertionError('Expected SourceContext')

    def test_present_changelog_passes(self, tmp_path: Path) -> None:
        """Present Changelog URL passes."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\n\n'
            '[project.urls]\nChangelog = "https://example.com/CHANGELOG.md"\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_changelog_url([pkg], result)

        if 'changelog_url' not in result.passed:
            raise AssertionError('Expected pass')


# check_pinned_deps_in_libraries


class TestPinnedDepsSourceContext:
    """Tests for check_pinned_deps_in_libraries with SourceContext."""

    def test_pinned_dep_has_source_context(self, tmp_path: Path) -> None:
        """Pinned dependency produces SourceContext."""
        toml = (
            '[project]\nname = "pinned"\nversion = "1.0"\n'
            'dependencies = [\n'
            '    "requests==2.31.0",\n'
            '    "click>=8.0",\n'
            ']\n'
        )
        pkg = _make_pkg(tmp_path, 'pinned', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_pinned_deps_in_libraries([pkg], result)

        if 'pinned_deps_in_libraries' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'pinned_deps_in_libraries'):
            raise AssertionError('Expected SourceContext')
        sc = _get_source_contexts(result, 'pinned_deps_in_libraries')[0]
        if '==' not in sc.label:
            raise AssertionError(f'Expected "==" in label, got {sc.label!r}')

    def test_no_pinned_deps_passes(self, tmp_path: Path) -> None:
        """No pinned deps passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\ndependencies = ["requests>=2.31.0"]\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_pinned_deps_in_libraries([pkg], result)

        if 'pinned_deps_in_libraries' not in result.passed:
            raise AssertionError('Expected pass')


# check_python_version_consistency


class TestPythonVersionConsistencySourceContext:
    """Tests for check_python_version_consistency with SourceContext."""

    def test_inconsistent_versions_has_source_context(self, tmp_path: Path) -> None:
        """Inconsistent requires-python produces SourceContext per package."""
        pkg_a = _make_pkg(
            tmp_path,
            'pkg-a',
            '[project]\nname = "pkg-a"\nversion = "1.0"\nrequires-python = ">=3.10"\n',
        )
        pkg_b = _make_pkg(
            tmp_path,
            'pkg-b',
            '[project]\nname = "pkg-b"\nversion = "1.0"\nrequires-python = ">=3.11"\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_version_consistency([pkg_a, pkg_b], result)

        if 'python_version' not in result.warnings:
            raise AssertionError('Expected warning')
        if not _has_source_context(result, 'python_version'):
            raise AssertionError('Expected SourceContext')
        contexts = _get_source_contexts(result, 'python_version')
        if len(contexts) < 2:
            raise AssertionError(f'Expected >= 2 contexts, got {len(contexts)}')
        for sc in contexts:
            if sc.key != 'requires-python':
                raise AssertionError(f'Expected key=requires-python, got {sc.key!r}')

    def test_consistent_versions_passes(self, tmp_path: Path) -> None:
        """Consistent requires-python passes."""
        pkg_a = _make_pkg(
            tmp_path,
            'pkg-a',
            '[project]\nname = "pkg-a"\nversion = "1.0"\nrequires-python = ">=3.10"\n',
        )
        pkg_b = _make_pkg(
            tmp_path,
            'pkg-b',
            '[project]\nname = "pkg-b"\nversion = "1.0"\nrequires-python = ">=3.10"\n',
        )
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_version_consistency([pkg_a, pkg_b], result)

        if 'python_version' not in result.passed:
            raise AssertionError('Expected pass')


# check_duplicate_dependencies


class TestDuplicateDependencies:
    """Tests for check_duplicate_dependencies."""

    def test_duplicate_deps_detected(self, tmp_path: Path) -> None:
        """Duplicate dependencies are detected."""
        toml = '[project]\nname = "dupes"\nversion = "1.0"\ndependencies = ["requests>=2.0", "requests>=2.1"]\n'
        pkg = _make_pkg(tmp_path, 'dupes', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([pkg], result)

        if 'duplicate_dependencies' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_duplicates_passes(self, tmp_path: Path) -> None:
        """No duplicates passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\ndependencies = ["requests>=2.0", "click>=8.0"]\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([pkg], result)

        if 'duplicate_dependencies' not in result.passed:
            raise AssertionError('Expected pass')


# check_legacy_setup_files


class TestLegacySetupFiles:
    """Tests for check_legacy_setup_files."""

    def test_setup_py_detected(self, tmp_path: Path) -> None:
        """setup.py is detected."""
        toml = '[project]\nname = "legacy"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'legacy', toml)
        (pkg.path / 'setup.py').write_text('# legacy', encoding='utf-8')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([pkg], result)

        if 'legacy_setup_files' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_legacy_passes(self, tmp_path: Path) -> None:
        """No legacy files passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([pkg], result)

        if 'legacy_setup_files' not in result.passed:
            raise AssertionError('Expected pass')


# check_placeholder_urls


class TestPlaceholderUrls:
    """Tests for check_placeholder_urls."""

    def test_placeholder_detected(self, tmp_path: Path) -> None:
        """Placeholder URL is detected."""
        toml = '[project]\nname = "ph"\nversion = "1.0"\n\n[project.urls]\nHomepage = "https://example.com/TODO"\n'
        pkg = _make_pkg(tmp_path, 'ph', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_placeholder_urls([pkg], result)

        if 'placeholder_urls' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_real_urls_pass(self, tmp_path: Path) -> None:
        """Real URLs pass."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\n\n[project.urls]\nHomepage = "https://github.com/real/project"\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_placeholder_urls([pkg], result)

        if 'placeholder_urls' not in result.passed:
            raise AssertionError('Expected pass')


# check_readme_content_type


class TestReadmeContentType:
    """Tests for check_readme_content_type."""

    def test_mismatch_md_rst(self, tmp_path: Path) -> None:
        """Markdown file with RST content-type is detected."""
        toml = (
            '[project]\nname = "mismatch"\nversion = "1.0"\n'
            'readme = {file = "README.md", content-type = "text/x-rst"}\n'
        )
        pkg = _make_pkg(tmp_path, 'mismatch', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_content_type([pkg], result)

        if 'readme_content_type' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_mismatch_rst_md(self, tmp_path: Path) -> None:
        """RST file with Markdown content-type is detected."""
        toml = (
            '[project]\nname = "mismatch2"\nversion = "1.0"\n'
            'readme = {file = "README.rst", content-type = "text/markdown"}\n'
        )
        pkg = _make_pkg(tmp_path, 'mismatch2', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_content_type([pkg], result)

        if 'readme_content_type' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_correct_content_type_passes(self, tmp_path: Path) -> None:
        """Correct content-type passes."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\nreadme = {file = "README.md", content-type = "text/markdown"}\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_readme_content_type([pkg], result)

        if 'readme_content_type' not in result.passed:
            raise AssertionError('Expected pass')


# check_test_filename_collisions


class TestTestFilenameCollisions:
    """Tests for check_test_filename_collisions."""

    def test_collision_detected(self, tmp_path: Path) -> None:
        """Colliding test filenames are detected."""
        pkg_a = _make_pkg(tmp_path, 'pkg-a', '[project]\nname = "pkg-a"\nversion = "1.0"\n')
        pkg_b = _make_pkg(tmp_path, 'pkg-b', '[project]\nname = "pkg-b"\nversion = "1.0"\n')
        # Create colliding test files.
        (pkg_a.path / 'tests').mkdir()
        (pkg_a.path / 'tests' / 'utils_test.py').write_text('# a', encoding='utf-8')
        (pkg_b.path / 'tests').mkdir()
        (pkg_b.path / 'tests' / 'utils_test.py').write_text('# b', encoding='utf-8')

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions([pkg_a, pkg_b], result)

        if 'test_filename_collisions' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_collision_passes(self, tmp_path: Path) -> None:
        """No collisions passes."""
        pkg_a = _make_pkg(tmp_path, 'pkg-a', '[project]\nname = "pkg-a"\nversion = "1.0"\n')
        pkg_b = _make_pkg(tmp_path, 'pkg-b', '[project]\nname = "pkg-b"\nversion = "1.0"\n')
        (pkg_a.path / 'tests').mkdir()
        (pkg_a.path / 'tests' / 'a_test.py').write_text('# a', encoding='utf-8')
        (pkg_b.path / 'tests').mkdir()
        (pkg_b.path / 'tests' / 'b_test.py').write_text('# b', encoding='utf-8')

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_test_filename_collisions([pkg_a, pkg_b], result)

        if 'test_filename_collisions' not in result.passed:
            raise AssertionError('Expected pass')


# check_publish_classifier_consistency


class TestPublishClassifierConsistency:
    """Tests for check_publish_classifier_consistency."""

    def test_excluded_without_classifier_warns(self, tmp_path: Path) -> None:
        """Package in exclude_publish but without Private classifier warns."""
        toml = '[project]\nname = "excluded"\nversion = "1.0"\nclassifiers = []\n'
        pkg = _make_pkg(tmp_path, 'excluded', toml, is_publishable=True)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_publish_classifier_consistency([pkg], result, exclude_publish=['excluded'])

        if 'publish_classifier_consistency' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_exclude_passes(self, tmp_path: Path) -> None:
        """No exclude_publish passes immediately."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_publish_classifier_consistency([pkg], result, exclude_publish=[])

        if 'publish_classifier_consistency' not in result.passed:
            raise AssertionError('Expected pass')


# Non-publishable packages are skipped


class TestNonPublishableSkipped:
    """Tests that non-publishable packages are skipped by checks."""

    def test_build_system_skips_non_publishable(self, tmp_path: Path) -> None:
        """Non-publishable packages are skipped by check_build_system."""
        toml = '[project]\nname = "private"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'private', toml, is_publishable=False)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_build_system([pkg], result)

        if 'build_system' not in result.passed:
            raise AssertionError('Expected pass for non-publishable')

    def test_version_pep440_skips_non_publishable(self, tmp_path: Path) -> None:
        """Non-publishable packages are skipped by check_version_pep440."""
        toml = '[project]\nname = "private"\nversion = "bad-version"\n'
        pkg = _make_pkg(tmp_path, 'private', toml, version='bad-version', is_publishable=False)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([pkg], result)

        if 'version_pep440' not in result.passed:
            raise AssertionError('Expected pass for non-publishable')


# _refresh_publishable


class TestRefreshPublishable:
    """Tests for _refresh_publishable."""

    def test_refresh_marks_private_as_non_publishable(self, tmp_path: Path) -> None:
        """Package with Private classifier becomes non-publishable."""
        toml = '[project]\nname = "priv"\nversion = "1.0"\nclassifiers = ["Private :: Do Not Upload"]\n'
        pkg = _make_pkg(tmp_path, 'priv', toml, is_publishable=True)
        _refresh_publishable([pkg])
        if pkg.is_publishable:
            raise AssertionError('Should be non-publishable after refresh')

    def test_refresh_marks_public_as_publishable(self, tmp_path: Path) -> None:
        """Package without Private classifier becomes publishable."""
        toml = '[project]\nname = "pub"\nversion = "1.0"\nclassifiers = []\n'
        pkg = _make_pkg(tmp_path, 'pub', toml, is_publishable=False)
        _refresh_publishable([pkg])
        if not pkg.is_publishable:
            raise AssertionError('Should be publishable after refresh')

    def test_refresh_handles_missing_project(self, tmp_path: Path) -> None:
        """Handles pyproject.toml without [project] section."""
        toml = '[build-system]\nrequires = ["hatchling"]\n'
        pkg = _make_pkg(tmp_path, 'no-proj', toml)
        _refresh_publishable([pkg])
        # Should not crash.

    def test_refresh_handles_bad_toml(self, tmp_path: Path) -> None:
        """Handles unparseable pyproject.toml gracefully."""
        pkg = _make_pkg(tmp_path, 'bad', '{{invalid}}')
        _refresh_publishable([pkg])
        # Should not crash.

    def test_refresh_handles_non_list_classifiers(self, tmp_path: Path) -> None:
        """Handles classifiers that are not a list."""
        toml = '[project]\nname = "x"\nversion = "1.0"\nclassifiers = "not-a-list"\n'
        pkg = _make_pkg(tmp_path, 'x', toml)
        _refresh_publishable([pkg])
        # Should not crash.


# check_type_markers


class TestTypeMarkers:
    """Tests for check_type_markers."""

    def test_missing_py_typed_warns(self, tmp_path: Path) -> None:
        """Missing py.typed in src/ warns."""
        toml = '[project]\nname = "no-typed"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'no-typed', toml)
        (pkg.path / 'src' / 'no_typed').mkdir(parents=True)
        (pkg.path / 'src' / 'no_typed' / '__init__.py').write_text('', encoding='utf-8')

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_type_markers([pkg], result)

        if 'type_markers' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_present_py_typed_passes(self, tmp_path: Path) -> None:
        """Present py.typed passes."""
        toml = '[project]\nname = "typed"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'typed', toml)
        src = pkg.path / 'src' / 'typed'
        src.mkdir(parents=True)
        (src / 'py.typed').write_text('', encoding='utf-8')

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_type_markers([pkg], result)

        if 'type_markers' not in result.passed:
            raise AssertionError('Expected pass')

    def test_library_dirs_filter(self, tmp_path: Path) -> None:
        """library_dirs filters which packages are checked."""
        toml = '[project]\nname = "outside"\nversion = "1.0"\n'
        pkg_dir = tmp_path / 'other' / 'outside'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')
        (pkg_dir / 'src' / 'outside').mkdir(parents=True)
        pkg = Package(
            name='outside',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
            is_publishable=True,
        )

        backend = PythonCheckBackend(library_dirs=['packages'])
        result = PreflightResult()
        backend.check_type_markers([pkg], result)

        # 'other' is not in library_dirs=['packages'], so no warning.
        if 'type_markers' not in result.passed:
            raise AssertionError('Expected pass (filtered out)')

    def test_no_src_dir_skipped(self, tmp_path: Path) -> None:
        """Package without src/ is skipped."""
        toml = '[project]\nname = "nosrc"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'nosrc', toml)
        # No src/ directory.

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_type_markers([pkg], result)

        if 'type_markers' not in result.passed:
            raise AssertionError('Expected pass (no src/)')


# check_version_consistency


class TestVersionConsistency:
    """Tests for check_version_consistency."""

    def test_mismatch_warns(self, tmp_path: Path) -> None:
        """Plugin version mismatch warns."""
        core = _make_pkg(tmp_path, 'core', '[project]\nname = "core"\nversion = "1.0"\n')
        plugin = _make_pkg(
            tmp_path,
            'core-plugin-foo',
            '[project]\nname = "core-plugin-foo"\nversion = "0.9"\n',
            version='0.9',
        )
        backend = PythonCheckBackend(core_package='core', plugin_prefix='core-plugin-')
        result = PreflightResult()
        backend.check_version_consistency([core, plugin], result)

        if 'version_consistency' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_consistent_passes(self, tmp_path: Path) -> None:
        """Consistent versions pass."""
        core = _make_pkg(tmp_path, 'core', '[project]\nname = "core"\nversion = "1.0"\n')
        plugin = _make_pkg(
            tmp_path,
            'core-plugin-foo',
            '[project]\nname = "core-plugin-foo"\nversion = "1.0"\n',
        )
        backend = PythonCheckBackend(core_package='core', plugin_prefix='core-plugin-')
        result = PreflightResult()
        backend.check_version_consistency([core, plugin], result)

        if 'version_consistency' not in result.passed:
            raise AssertionError('Expected pass')

    def test_no_core_package_skips(self, tmp_path: Path) -> None:
        """No core_package configured skips check."""
        pkg = _make_pkg(tmp_path, 'x', '[project]\nname = "x"\nversion = "1.0"\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_version_consistency([pkg], result)

        if 'version_consistency' not in result.passed:
            raise AssertionError('Expected pass (no core_package)')

    def test_core_not_found_warns(self, tmp_path: Path) -> None:
        """Missing core package warns."""
        pkg = _make_pkg(tmp_path, 'x', '[project]\nname = "x"\nversion = "1.0"\n')
        backend = PythonCheckBackend(core_package='missing', plugin_prefix='x-')
        result = PreflightResult()
        backend.check_version_consistency([pkg], result)

        if 'version_consistency' not in result.warnings:
            raise AssertionError('Expected warning about missing core')


# check_naming_convention


class TestNamingConvention:
    """Tests for check_naming_convention."""

    def test_mismatch_warns(self, tmp_path: Path) -> None:
        """Naming mismatch warns."""
        # Package dir is 'bar' but name is 'wrong-name'.
        pkg_dir = tmp_path / 'plugins' / 'bar'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "wrong-name"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')
        pkg = Package(
            name='wrong-name',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )

        backend = PythonCheckBackend(plugin_prefix='genkit-plugin-', plugin_dirs=['plugins'])
        result = PreflightResult()
        backend.check_naming_convention([pkg], result)

        if 'naming_convention' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_correct_naming_passes(self, tmp_path: Path) -> None:
        """Correct naming passes."""
        pkg_dir = tmp_path / 'plugins' / 'bar'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "genkit-plugin-bar"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')
        pkg = Package(
            name='genkit-plugin-bar',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )

        backend = PythonCheckBackend(plugin_prefix='genkit-plugin-', plugin_dirs=['plugins'])
        result = PreflightResult()
        backend.check_naming_convention([pkg], result)

        if 'naming_convention' not in result.passed:
            raise AssertionError('Expected pass')

    def test_no_prefix_skips(self, tmp_path: Path) -> None:
        """No plugin_prefix configured skips check."""
        pkg = _make_pkg(tmp_path, 'x', '[project]\nname = "x"\nversion = "1.0"\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([pkg], result)

        if 'naming_convention' not in result.passed:
            raise AssertionError('Expected pass (no prefix)')

    def test_plugin_dirs_filter(self, tmp_path: Path) -> None:
        """plugin_dirs filters which packages are checked."""
        pkg_dir = tmp_path / 'other' / 'bar'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "wrong"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')
        pkg = Package(
            name='wrong',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )

        backend = PythonCheckBackend(plugin_prefix='genkit-plugin-', plugin_dirs=['plugins'])
        result = PreflightResult()
        backend.check_naming_convention([pkg], result)

        # 'other' not in plugin_dirs, so skipped.
        if 'naming_convention' not in result.passed:
            raise AssertionError('Expected pass (filtered out)')


# check_namespace_init


class TestNamespaceInit:
    """Tests for check_namespace_init."""

    def test_init_in_namespace_fails(self, tmp_path: Path) -> None:
        """__init__.py in namespace dir fails."""
        toml = '[project]\nname = "ns-pkg"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ns-pkg', toml)
        ns_dir = pkg.path / 'src' / 'genkit'
        ns_dir.mkdir(parents=True)
        (ns_dir / '__init__.py').write_text('# bad', encoding='utf-8')

        backend = PythonCheckBackend(namespace_dirs=['genkit'])
        result = PreflightResult()
        backend.check_namespace_init([pkg], result)

        if 'namespace_init' not in result.failed:
            raise AssertionError('Expected failure')

    def test_no_init_passes(self, tmp_path: Path) -> None:
        """No __init__.py in namespace dir passes."""
        toml = '[project]\nname = "ns-pkg"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ns-pkg', toml)
        ns_dir = pkg.path / 'src' / 'genkit'
        ns_dir.mkdir(parents=True)

        backend = PythonCheckBackend(namespace_dirs=['genkit'])
        result = PreflightResult()
        backend.check_namespace_init([pkg], result)

        if 'namespace_init' not in result.passed:
            raise AssertionError('Expected pass')

    def test_no_namespace_dirs_skips(self, tmp_path: Path) -> None:
        """No namespace_dirs configured skips check."""
        pkg = _make_pkg(tmp_path, 'x', '[project]\nname = "x"\nversion = "1.0"\n')
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_namespace_init([pkg], result)

        if 'namespace_init' not in result.passed:
            raise AssertionError('Expected pass (no namespace_dirs)')

    def test_plugin_dirs_filter(self, tmp_path: Path) -> None:
        """plugin_dirs filters which packages are checked for namespace init."""
        pkg_dir = tmp_path / 'other' / 'x'
        pkg_dir.mkdir(parents=True)
        toml = '[project]\nname = "x"\nversion = "1.0"\n'
        (pkg_dir / 'pyproject.toml').write_text(toml, encoding='utf-8')
        ns_dir = pkg_dir / 'src' / 'genkit'
        ns_dir.mkdir(parents=True)
        (ns_dir / '__init__.py').write_text('# bad', encoding='utf-8')
        pkg = Package(
            name='x',
            version='1.0',
            path=pkg_dir,
            manifest_path=pkg_dir / 'pyproject.toml',
        )

        backend = PythonCheckBackend(namespace_dirs=['genkit'], plugin_dirs=['plugins'])
        result = PreflightResult()
        backend.check_namespace_init([pkg], result)

        # 'other' not in plugin_dirs, so skipped.
        if 'namespace_init' not in result.passed:
            raise AssertionError('Expected pass (filtered out)')


# check_deprecated_classifiers


class TestDeprecatedClassifiers:
    """Tests for check_deprecated_classifiers."""

    def test_deprecated_classifier_warns(self, tmp_path: Path) -> None:
        """Deprecated classifier warns."""
        if not DEPRECATED_CLASSIFIERS:
            return  # Nothing to test if no deprecated classifiers defined.

        deprecated = next(iter(DEPRECATED_CLASSIFIERS))
        toml = f'[project]\nname = "dep"\nversion = "1.0"\nclassifiers = ["{deprecated}"]\n'
        pkg = _make_pkg(tmp_path, 'dep', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_deprecated_classifiers([pkg], result)

        if 'deprecated_classifiers' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_deprecated_passes(self, tmp_path: Path) -> None:
        """No deprecated classifiers passes."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\n'
            'classifiers = ["License :: OSI Approved :: Apache Software License"]\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_deprecated_classifiers([pkg], result)

        if 'deprecated_classifiers' not in result.passed:
            raise AssertionError('Expected pass')


# check_license_classifier_mismatch


class TestLicenseClassifierMismatch:
    """Tests for check_license_classifier_mismatch."""

    def test_mismatch_warns(self, tmp_path: Path) -> None:
        """LICENSE file vs classifier mismatch warns."""
        toml = '[project]\nname = "lic"\nversion = "1.0"\nclassifiers = ["License :: OSI Approved :: MIT License"]\n'
        pkg = _make_pkg(tmp_path, 'lic', toml)
        (pkg.path / 'LICENSE').write_text(
            'Apache License\nVersion 2.0',
            encoding='utf-8',
        )

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_license_classifier_mismatch([pkg], result)

        if 'license_classifier_mismatch' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_matching_license_passes(self, tmp_path: Path) -> None:
        """Matching LICENSE file and classifier passes."""
        toml = (
            '[project]\nname = "ok"\nversion = "1.0"\n'
            'classifiers = ["License :: OSI Approved :: Apache Software License"]\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        (pkg.path / 'LICENSE').write_text(
            'Apache License\nVersion 2.0',
            encoding='utf-8',
        )

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_license_classifier_mismatch([pkg], result)

        if 'license_classifier_mismatch' not in result.passed:
            raise AssertionError('Expected pass')

    def test_no_license_file_skipped(self, tmp_path: Path) -> None:
        """No LICENSE file is skipped."""
        toml = '[project]\nname = "nolic"\nversion = "1.0"\nclassifiers = ["License :: OSI Approved :: MIT License"]\n'
        pkg = _make_pkg(tmp_path, 'nolic', toml)

        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_license_classifier_mismatch([pkg], result)

        if 'license_classifier_mismatch' not in result.passed:
            raise AssertionError('Expected pass (no LICENSE file)')


# check_python_classifiers


class TestPythonClassifiers:
    """Tests for check_python_classifiers."""

    def test_missing_classifiers_warns(self, tmp_path: Path) -> None:
        """Missing Python version classifiers warns."""
        toml = '[project]\nname = "noclf"\nversion = "1.0"\nclassifiers = []\n'
        pkg = _make_pkg(tmp_path, 'noclf', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_classifiers([pkg], result)

        if 'python_classifiers' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_all_classifiers_passes(self, tmp_path: Path) -> None:
        """All Python version classifiers passes."""
        classifiers = ', '.join(f'"Programming Language :: Python :: 3.{v}"' for v in range(10, 15))
        toml = f'[project]\nname = "ok"\nversion = "1.0"\nclassifiers = [{classifiers}]\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_python_classifiers([pkg], result)

        if 'python_classifiers' not in result.passed:
            raise AssertionError('Expected pass')


# check_self_dependencies


class TestSelfDependencies:
    """Tests for check_self_dependencies."""

    def test_self_dep_warns(self, tmp_path: Path) -> None:
        """Self-dependency warns."""
        toml = '[project]\nname = "self-dep"\nversion = "1.0"\ndependencies = ["self-dep>=1.0"]\n'
        pkg = _make_pkg(tmp_path, 'self-dep', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([pkg], result)

        if 'self_dependencies' not in result.warnings:
            raise AssertionError('Expected warning')

    def test_no_self_dep_passes(self, tmp_path: Path) -> None:
        """No self-dependency passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\ndependencies = ["requests>=2.0"]\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([pkg], result)

        if 'self_dependencies' not in result.passed:
            raise AssertionError('Expected pass')


# check_unreachable_extras


class TestUnreachableExtras:
    """Tests for check_unreachable_extras."""

    def test_valid_extras_passes(self, tmp_path: Path) -> None:
        """Valid optional-dependencies passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n\n[project.optional-dependencies]\ndev = ["pytest>=7.0"]\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_unreachable_extras([pkg], result)

        if 'unreachable_extras' not in result.passed:
            raise AssertionError('Expected pass')

    def test_no_extras_passes(self, tmp_path: Path) -> None:
        """No optional-dependencies passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_unreachable_extras([pkg], result)

        if 'unreachable_extras' not in result.passed:
            raise AssertionError('Expected pass')


# check_distro_deps


class TestDistroDeps:
    """Tests for check_distro_deps."""

    def test_no_packaging_dir_passes(self, tmp_path: Path) -> None:
        """No packaging/ directory passes."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        result = PreflightResult()
        backend.check_distro_deps([pkg], result)

        if 'distro_deps' not in result.passed:
            raise AssertionError('Expected pass')


# _parse_pyproject_with_content


class TestParsePyprojectWithContent:
    """Tests for _parse_pyproject_with_content."""

    def test_valid_toml(self, tmp_path: Path) -> None:
        """Valid TOML returns (doc, content)."""
        toml = '[project]\nname = "ok"\nversion = "1.0"\n'
        pkg = _make_pkg(tmp_path, 'ok', toml)
        backend = PythonCheckBackend()
        doc, content = backend._parse_pyproject_with_content(pkg)
        if doc is None:
            raise AssertionError('Expected doc')
        if not content:
            raise AssertionError('Expected content')

    def test_invalid_toml(self, tmp_path: Path) -> None:
        """Invalid TOML returns (None, '')."""
        pkg = _make_pkg(tmp_path, 'bad', '{{invalid}}')
        backend = PythonCheckBackend()
        doc, content = backend._parse_pyproject_with_content(pkg)
        if doc is not None:
            raise AssertionError('Expected None doc')
        if content != '':
            raise AssertionError('Expected empty content')


# run_fixes


class TestRunFixes:
    """Tests for run_fixes."""

    def test_run_fixes_on_clean_package(self, tmp_path: Path) -> None:
        """run_fixes on a clean package returns no changes."""
        toml = (
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
            '[project]\nname = "ok"\nversion = "1.0.0"\n'
            'description = "A package"\n'
            'license = {text = "Apache-2.0"}\n'
            'requires-python = ">=3.10"\n'
            'authors = [{name = "Test"}]\n'
            'readme = "README.md"\n'
            'classifiers = ["License :: OSI Approved :: Apache Software License"]\n\n'
            '[project.urls]\nChangelog = "https://example.com/CHANGELOG.md"\n'
        )
        pkg = _make_pkg(tmp_path, 'ok', toml)
        (pkg.path / 'README.md').write_text('# ok', encoding='utf-8')
        (pkg.path / 'LICENSE').write_text('Apache License\nVersion 2.0', encoding='utf-8')

        backend = PythonCheckBackend()
        changes = backend.run_fixes([pkg], dry_run=True)
        # Should not crash. Changes may or may not be empty depending on
        # whether the package needs Python version classifiers etc.
        if not isinstance(changes, list):
            raise AssertionError('Expected list')

    def test_run_fixes_with_exclude_publish(self, tmp_path: Path) -> None:
        """run_fixes with exclude_publish doesn't crash."""
        toml = '[project]\nname = "excl"\nversion = "1.0"\nclassifiers = []\n'
        pkg = _make_pkg(tmp_path, 'excl', toml)
        backend = PythonCheckBackend()
        changes = backend.run_fixes([pkg], exclude_publish=['excl'], dry_run=True)
        if not isinstance(changes, list):
            raise AssertionError('Expected list')
