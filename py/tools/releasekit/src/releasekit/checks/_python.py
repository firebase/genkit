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

"""Python-specific workspace check backend (``PythonCheckBackend``)."""

from __future__ import annotations

import fnmatch
import subprocess  # noqa: S404 - intentional use for uv pip check
from pathlib import Path

import tomlkit

from releasekit.checks._constants import (
    _PRIVATE_CLASSIFIER,
    _DEP_NAME_RE,
    _LICENSE_PATTERNS,
    _PEP440_RE,
    _PLACEHOLDER_URL_PATTERNS,
    DEPRECATED_CLASSIFIERS,
)
from releasekit.checks._python_fixers import (
    fix_build_system,
    fix_changelog_url,
    fix_deprecated_classifiers,
    fix_duplicate_dependencies,
    fix_license_classifier_mismatch,
    fix_namespace_init,
    fix_placeholder_urls,
    fix_publish_classifiers,
    fix_readme_content_type,
    fix_readme_field,
    fix_requires_python,
    fix_self_dependencies,
    fix_type_markers,
    fix_version_field,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

logger = get_logger(__name__)


def _refresh_publishable(packages: list[Package]) -> None:
    """Re-read classifiers from disk and update ``is_publishable`` in-place.

    After ``fix_publish_classifiers`` modifies the ``Private :: Do Not
    Upload`` classifier on disk, the in-memory ``Package.is_publishable``
    field is stale.  This function re-reads each package's
    ``pyproject.toml`` and updates the field so that subsequent fixers
    (``fix_readme_field``, ``fix_changelog_url``, etc.) that gate on
    ``is_publishable`` see the correct value.
    """
    for pkg in packages:
        try:
            content = pkg.pyproject_path.read_text(encoding='utf-8')
            doc = tomlkit.parse(content)
        except Exception:
            continue
        project = doc.get('project')
        if not isinstance(project, dict):
            continue
        classifiers = project.get('classifiers', [])
        if not isinstance(classifiers, list):
            continue
        new_value = not any(
            isinstance(c, str) and _PRIVATE_CLASSIFIER in c
            for c in classifiers
        )
        object.__setattr__(pkg, 'is_publishable', new_value)


class PythonCheckBackend:
    """Python-specific workspace checks for uv/pip workspaces.

    Checks for:
    - ``py.typed`` PEP 561 markers in library packages
    - Version consistency with a core package
    - ``{plugin_prefix}{dir}`` naming convention
    - ``pyproject.toml`` metadata completeness (description, authors, license)

    Args:
        core_package: Name of the core package for version consistency
            checks. If empty, version consistency check is skipped.
        plugin_prefix: Expected prefix for package names in
            ``plugin_dirs``. If empty, naming convention check is
            skipped.
        namespace_dirs: Relative paths (from ``src/``) of PEP 420
            namespace directories that must NOT contain
            ``__init__.py``. If empty, namespace init check is
            skipped.
        library_dirs: Parent directory names whose children are
            publishable library packages requiring ``py.typed``
            markers (e.g. ``["packages", "plugins"]``). If empty,
            the check applies to all publishable packages.
        plugin_dirs: Parent directory names whose children follow
            the ``plugin_prefix`` naming convention and need PEP 420
            namespace init checks (e.g. ``["plugins"]``). If empty,
            naming convention and namespace init checks apply to all
            packages.
    """

    def __init__(
        self,
        *,
        core_package: str = '',
        plugin_prefix: str = '',
        namespace_dirs: list[str] | None = None,
        library_dirs: list[str] | None = None,
        plugin_dirs: list[str] | None = None,
    ) -> None:
        """Initialize with optional project-specific configuration."""
        self._core_package = core_package
        self._plugin_prefix = plugin_prefix
        self._namespace_dirs = namespace_dirs or []
        self._library_dirs: frozenset[str] = frozenset(library_dirs) if library_dirs else frozenset()
        self._plugin_dirs: frozenset[str] = frozenset(plugin_dirs) if plugin_dirs else frozenset()

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that library packages have a ``py.typed`` PEP 561 marker.

        If ``library_dirs`` is configured, only checks packages whose
        parent directory name is in that set. Otherwise checks all
        publishable packages with a ``src/`` directory.
        """
        check_name = 'type_markers'
        missing: list[str] = []
        for pkg in packages:
            if not pkg.is_publishable:
                continue
            if self._library_dirs and pkg.path.parent.name not in self._library_dirs:
                continue
            src_dir = pkg.path / 'src'
            if not src_dir.exists():
                continue
            py_typed_files = list(src_dir.rglob('py.typed'))
            if not py_typed_files:
                missing.append(pkg.name)
        if missing:
            result.add_warning(
                check_name,
                f'Missing py.typed marker: {", ".join(missing)}',
            )
        else:
            result.add_pass(check_name)

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all plugin packages match the core package version."""
        check_name = 'version_consistency'
        if not self._core_package or not self._plugin_prefix:
            result.add_pass(check_name)
            return

        core_pkg = next((p for p in packages if p.name == self._core_package), None)
        if core_pkg is None:
            result.add_warning(
                check_name,
                f'Core "{self._core_package}" package not found; cannot verify versions.',
            )
            return

        core_version = core_pkg.version
        mismatches: list[str] = []
        for pkg in packages:
            if not pkg.name.startswith(self._plugin_prefix):
                continue
            if pkg.version != core_version:
                mismatches.append(
                    f'{pkg.name}=={pkg.version} (expected {core_version})',
                )

        if mismatches:
            result.add_warning(
                check_name,
                f'Plugin version mismatches: {", ".join(mismatches)}',
            )
        else:
            result.add_pass(check_name)

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check ``{plugin_prefix}{dir}`` naming convention.

        If ``plugin_dirs`` is configured, only checks packages whose
        parent directory name is in that set. Otherwise checks all
        packages.
        """
        check_name = 'naming_convention'
        if not self._plugin_prefix:
            result.add_pass(check_name)
            return

        mismatches: list[str] = []
        for pkg in packages:
            dir_name = pkg.path.name
            parent_name = pkg.path.parent.name

            if self._plugin_dirs and parent_name not in self._plugin_dirs:
                continue

            expected = f'{self._plugin_prefix}{dir_name}'
            if pkg.name != expected:
                mismatches.append(
                    f'{dir_name}/ → {pkg.name} (expected {expected})',
                )

        if mismatches:
            result.add_warning(
                check_name,
                f'Naming mismatches: {", ".join(mismatches)}',
            )
        else:
            result.add_pass(check_name)

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check ``pyproject.toml`` has description, authors, and license."""
        check_name = 'metadata_completeness'
        required_fields = ['description', 'authors', 'license']
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                issues.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue

            project: dict[str, object] = data.get('project', {})
            missing_fields: list[str] = []
            for field_name in required_fields:
                if field_name not in project or not project[field_name]:
                    missing_fields.append(field_name)

            if missing_fields:
                issues.append(
                    f'{pkg.name}: missing {", ".join(missing_fields)}',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Incomplete metadata: {"; ".join(issues)}',
            )
        else:
            result.add_pass(check_name)

    def check_python_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages declare the same ``requires-python``.

        Mixed Python version requirements within a workspace cause install
        failures and CI matrix confusion. All publishable packages should
        agree on the minimum supported Python version.
        """
        check_name = 'python_version'
        versions: dict[str, list[str]] = {}

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                logger.debug('parse_failed', path=str(pkg.pyproject_path))
                continue

            project: dict[str, object] = data.get('project', {})
            requires_python = project.get('requires-python')
            if isinstance(requires_python, str):
                versions.setdefault(requires_python, []).append(pkg.name)

        if not versions:
            result.add_pass(check_name)
            return

        if len(versions) == 1:
            result.add_pass(check_name)
        else:
            parts: list[str] = []
            for ver, pkgs in sorted(versions.items()):
                parts.append(f'{ver}: {len(pkgs)} packages')
            result.add_warning(
                check_name,
                f'Inconsistent requires-python: {"; ".join(parts)}',
            )

    def check_python_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check publishable packages have Python 3.10–3.14 classifiers.

        Missing classifiers cause PyPI to display incorrect Python version
        support. All publishable packages should include
        ``Programming Language :: Python :: 3.{10..14}`` classifiers.
        """
        check_name = 'python_classifiers'
        expected_versions = {'3.10', '3.11', '3.12', '3.13', '3.14'}
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                logger.debug('parse_failed', path=str(pkg.pyproject_path))
                continue

            project: dict[str, object] = data.get('project', {})
            classifiers = project.get('classifiers', [])
            if not isinstance(classifiers, list):
                continue

            # Extract Python version classifiers.
            found_versions: set[str] = set()
            prefix = 'Programming Language :: Python :: '
            for classifier in classifiers:
                if isinstance(classifier, str) and classifier.startswith(prefix):
                    version = classifier[len(prefix) :]
                    found_versions.add(version)

            missing = expected_versions - found_versions
            if missing:
                issues.append(
                    f'{pkg.name}: missing classifiers for Python {", ".join(sorted(missing))}',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Missing Python classifiers: {"; ".join(issues)}',
            )
        else:
            result.add_pass(check_name)

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Run ``uv pip check`` to verify all dependencies resolve.

        This catches missing, incompatible, or conflicting dependencies
        before a release attempt. Requires ``uv`` to be installed.
        """
        check_name = 'dependency_resolution'
        try:
            proc = subprocess.run(  # noqa: S603 - intentional subprocess call
                ['uv', 'pip', 'check'],  # noqa: S607 - uv is a known tool
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            result.add_warning(
                check_name,
                'uv not found; skipping dependency resolution check.',
            )
            return
        except subprocess.TimeoutExpired:
            result.add_warning(
                check_name,
                'uv pip check timed out after 60 seconds.',
            )
            return

        if proc.returncode == 0:
            result.add_pass(check_name)
        else:
            output = (proc.stdout or proc.stderr or '').strip()
            # Truncate long output to keep error messages readable.
            if len(output) > 500:
                output = output[:500] + '...'
            result.add_warning(
                check_name,
                f'Dependency issues: {output}',
            )

    def check_namespace_init(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for accidental ``__init__.py`` in PEP 420 namespace directories.

        Namespace packages must NOT have ``__init__.py`` in intermediate
        directories. An accidental ``__init__.py`` breaks ``pip install``
        by preventing Python from discovering contributions from other
        packages in the same namespace.

        If ``plugin_dirs`` is configured, only checks packages whose
        parent directory name is in that set. Otherwise checks all
        packages.
        """
        check_name = 'namespace_init'
        if not self._namespace_dirs:
            result.add_pass(check_name)
            return

        offenders: list[str] = []

        for pkg in packages:
            if self._plugin_dirs and pkg.path.parent.name not in self._plugin_dirs:
                continue
            src_dir = pkg.path / 'src'
            if not src_dir.exists():
                continue

            for ns_dir in self._namespace_dirs:
                init_file = src_dir / ns_dir / '__init__.py'
                if init_file.exists():
                    relative = init_file.relative_to(pkg.path)
                    offenders.append(f'{pkg.name}: {relative}')

        if offenders:
            result.add_failure(
                check_name,
                f'Namespace dirs must not have __init__.py: {", ".join(offenders)}',
            )
        else:
            result.add_pass(check_name)

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``readme`` in ``[project]``.

        Without ``readme``, PyPI displays an empty page body — no
        description, no usage instructions, nothing. This is the single
        most impactful metadata field for user experience on PyPI.
        """
        check_name = 'readme_field'
        missing: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                missing.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue

            project: dict[str, object] = data.get('project', {})
            if 'readme' not in project or not project['readme']:
                missing.append(pkg.name)

        if missing:
            result.add_warning(
                check_name,
                f'Missing readme field: {", ".join(missing)}',
                hint='Add readme = "README.md" to the [project] section in pyproject.toml.',
            )
        else:
            result.add_pass(check_name)

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have a ``Changelog`` entry in ``[project.urls]``.

        PyPI renders URL entries as sidebar links. The ``Changelog`` key
        is a well-known convention (alongside ``Homepage``, ``Repository``,
        ``Documentation``, ``Bug Tracker``) that users expect.
        """
        check_name = 'changelog_url'
        missing: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                missing.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue

            project: dict[str, object] = data.get('project', {})
            urls_val = project.get('urls', {})
            urls = urls_val if isinstance(urls_val, dict) else {}
            has_changelog = any(key.lower() == 'changelog' for key in urls)
            if not has_changelog:
                missing.append(pkg.name)

        if missing:
            result.add_warning(
                check_name,
                f'Missing Changelog URL in [project.urls]: {", ".join(missing)}',
                hint='Add Changelog = "https://github.com/.../CHANGELOG.md" to [project.urls] in pyproject.toml.',
            )
        else:
            result.add_pass(check_name)

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``Private :: Do Not Upload`` classifier is consistent.

        Warns when:
        - A package is scheduled for publish (not in ``exclude_publish``)
          but has the ``Private :: Do Not Upload`` classifier.
        - A package is in ``exclude_publish`` but does NOT have the
          classifier (the config and the classifier should agree).
        """
        check_name = 'publish_classifier_consistency'
        if not exclude_publish:
            result.add_pass(check_name)
            return

        issues: list[str] = []
        for pkg in packages:
            is_excluded = any(fnmatch.fnmatch(pkg.name, pat) for pat in exclude_publish)
            has_private_classifier = not pkg.is_publishable

            if not is_excluded and has_private_classifier:
                issues.append(
                    f'{pkg.name}: has Private :: Do Not Upload but is NOT in exclude_publish',
                )
            elif is_excluded and not has_private_classifier:
                issues.append(
                    f'{pkg.name}: in exclude_publish but missing Private :: Do Not Upload classifier',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Publish classifier mismatch: {"; ".join(issues)}',
                hint='Ensure exclude_publish patterns and Private :: Do Not Upload classifiers agree.',
            )
        else:
            result.add_pass(check_name)

    def check_test_filename_collisions(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for test files with identical relative paths across packages.

        When two packages contain a test file at the same relative path
        (e.g. ``tests/utils_test.py``), pytest may silently shadow one of
        them depending on collection order and ``rootdir`` configuration.
        This means tests can stop running without any visible error.

        The check scans each package's ``tests/`` directory (if present)
        and flags any relative path that appears in more than one package.
        """
        check_name = 'test_filename_collisions'

        # Map: relative test path → list of package names that contain it.
        seen: dict[str, list[str]] = {}

        for pkg in packages:
            tests_dir = pkg.path / 'tests'
            if not tests_dir.is_dir():
                continue
            for test_file in tests_dir.rglob('*_test.py'):
                rel = test_file.relative_to(pkg.path)
                seen.setdefault(str(rel), []).append(pkg.name)
            for test_file in tests_dir.rglob('test_*.py'):
                rel = test_file.relative_to(pkg.path)
                seen.setdefault(str(rel), []).append(pkg.name)

        collisions: list[str] = []
        for rel_path, pkg_names in sorted(seen.items()):
            if len(pkg_names) > 1:
                collisions.append(f'{rel_path} in {", ".join(sorted(pkg_names))}')

        if collisions:
            result.add_warning(
                check_name,
                f'Test file collisions (pytest may shadow): {"; ".join(collisions)}',
                hint='Rename colliding test files to be unique across packages, '
                'e.g. tests/pkgname_utils_test.py instead of tests/utils_test.py.',
            )
        else:
            result.add_pass(check_name)

    @staticmethod
    def _parse_pyproject(pkg: Package) -> tomlkit.TOMLDocument | None:
        """Parse a package's pyproject.toml, returning the full doc or None."""
        try:
            content = pkg.pyproject_path.read_text(encoding='utf-8')
            return tomlkit.parse(content)
        except Exception:
            return None

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that ``[build-system]`` is present and has ``build-backend``."""
        check_name = 'build_system'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                issues.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue
            build_system = doc.get('build-system')
            if not isinstance(build_system, dict):
                issues.append(f'{pkg.name}: missing [build-system]')
            elif 'build-backend' not in build_system:
                issues.append(f'{pkg.name}: [build-system] missing build-backend')

        if issues:
            result.add_failure(
                check_name,
                f'Build system issues: {"; ".join(issues)}',
                hint='Add [build-system] with requires and build-backend to pyproject.toml.',
            )
        else:
            result.add_pass(check_name)

    def check_version_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that ``[project].version`` is present or declared dynamic."""
        check_name = 'version_field'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            has_version = 'version' in project and project['version']
            dynamic = project.get('dynamic', [])
            has_dynamic_version = isinstance(dynamic, list) and 'version' in dynamic
            if not has_version and not has_dynamic_version:
                issues.append(pkg.name)

        if issues:
            result.add_warning(
                check_name,
                f'Missing version field (will build as 0.0.0): {", ".join(issues)}',
                hint='Add version = "x.y.z" to [project] or add "version" to dynamic.',
            )
        else:
            result.add_pass(check_name)

    def check_duplicate_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for duplicate entries in ``[project.dependencies]``."""
        check_name = 'duplicate_dependencies'
        issues: list[str] = []

        for pkg in packages:
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            deps = project.get('dependencies', [])
            if not isinstance(deps, list):
                continue

            seen_names: dict[str, int] = {}
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                match = _DEP_NAME_RE.match(dep.strip())
                if match:
                    name = match.group(1).lower().replace('-', '_').replace('.', '_')
                    seen_names[name] = seen_names.get(name, 0) + 1

            dupes = [n for n, count in seen_names.items() if count > 1]
            if dupes:
                issues.append(f'{pkg.name}: {", ".join(sorted(dupes))}')

        if issues:
            result.add_warning(
                check_name,
                f'Duplicate dependencies: {"; ".join(issues)}',
                hint='Remove duplicate entries from [project.dependencies].',
            )
        else:
            result.add_pass(check_name)

    def check_pinned_deps_in_libraries(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable library packages don't pin deps with ``==``."""
        check_name = 'pinned_deps_in_libraries'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            deps = project.get('dependencies', [])
            if not isinstance(deps, list):
                continue

            pinned = [d for d in deps if isinstance(d, str) and '==' in d]
            if pinned:
                issues.append(f'{pkg.name}: {", ".join(pinned)}')

        if issues:
            result.add_warning(
                check_name,
                f'Pinned dependencies in libraries (use >= instead): {"; ".join(issues)}',
                hint='Libraries should use >= version specifiers, not ==, to avoid breaking downstream users.',
            )
        else:
            result.add_pass(check_name)

    def check_requires_python(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``requires-python``."""
        check_name = 'requires_python'
        missing: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            if 'requires-python' not in project or not project['requires-python']:
                missing.append(pkg.name)

        if missing:
            result.add_warning(
                check_name,
                f'Missing requires-python: {", ".join(missing)}',
                hint='Add requires-python = ">=3.10" (or appropriate version) to [project].',
            )
        else:
            result.add_pass(check_name)

    def check_readme_content_type(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that readme file extension matches content-type declaration."""
        check_name = 'readme_content_type'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue

            readme = project.get('readme')
            if not readme:
                continue

            # readme can be a string (path) or a table with file + content-type.
            if isinstance(readme, str):
                # Simple string form — no content-type to check.
                continue
            if isinstance(readme, dict):
                file_path = readme.get('file', '')
                content_type = readme.get('content-type', '')
                if not file_path or not content_type:
                    continue
                ext = Path(file_path).suffix.lower()
                if ext == '.md' and 'rst' in content_type.lower():
                    issues.append(f'{pkg.name}: {file_path} is Markdown but content-type is {content_type}')
                elif ext == '.rst' and 'markdown' in content_type.lower():
                    issues.append(f'{pkg.name}: {file_path} is RST but content-type is {content_type}')

        if issues:
            result.add_warning(
                check_name,
                f'Readme content-type mismatch: {"; ".join(issues)}',
                hint='Ensure readme file extension matches content-type (text/markdown for .md, text/x-rst for .rst).',
            )
        else:
            result.add_pass(check_name)

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package versions are PEP 440 compliant."""
        check_name = 'version_pep440'
        invalid: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            if pkg.version and not _PEP440_RE.match(pkg.version):
                invalid.append(f'{pkg.name}: {pkg.version!r}')

        if invalid:
            result.add_failure(
                check_name,
                f'Non-PEP 440 versions (PyPI will reject): {"; ".join(invalid)}',
                hint='Use PEP 440 compliant versions like 1.0.0, 1.0.0a1, 1.0.0.post1, etc.',
            )
        else:
            result.add_pass(check_name)

    def check_placeholder_urls(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for placeholder or empty URLs in ``[project.urls]``."""
        check_name = 'placeholder_urls'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            urls = project.get('urls')
            if not isinstance(urls, dict):
                continue

            for label, url in urls.items():
                if not isinstance(url, str):
                    continue
                url_lower = url.lower().strip()
                if not url_lower:
                    issues.append(f'{pkg.name}: [{label}] is empty')
                elif any(p.lower() in url_lower for p in _PLACEHOLDER_URL_PATTERNS):
                    issues.append(f'{pkg.name}: [{label}] = {url!r} looks like a placeholder')

        if issues:
            result.add_warning(
                check_name,
                f'Placeholder URLs: {"; ".join(issues)}',
                hint='Replace placeholder URLs in [project.urls] with real values.',
            )
        else:
            result.add_pass(check_name)

    def check_legacy_setup_files(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for leftover ``setup.py`` or ``setup.cfg`` files."""
        check_name = 'legacy_setup_files'
        found: list[str] = []

        for pkg in packages:
            for legacy in ('setup.py', 'setup.cfg'):
                if (pkg.path / legacy).exists():
                    found.append(f'{pkg.name}: {legacy}')

        if found:
            result.add_warning(
                check_name,
                f'Legacy setup files found: {"; ".join(found)}',
                hint='Remove setup.py/setup.cfg and use pyproject.toml exclusively.',
            )
        else:
            result.add_pass(check_name)

    def check_deprecated_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for deprecated trove classifiers."""
        check_name = 'deprecated_classifiers'
        issues: list[str] = []

        for pkg in packages:
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            classifiers = project.get('classifiers', [])
            if not isinstance(classifiers, list):
                continue

            for clf in classifiers:
                if not isinstance(clf, str):
                    continue
                if clf in DEPRECATED_CLASSIFIERS:
                    replacement = DEPRECATED_CLASSIFIERS[clf]
                    if replacement:
                        issues.append(f'{pkg.name}: {clf!r} → {replacement!r}')
                    else:
                        issues.append(f'{pkg.name}: {clf!r} (remove)')

        if issues:
            result.add_warning(
                check_name,
                f'Deprecated classifiers: {"; ".join(issues)}',
                hint='Run with --fix to auto-replace deprecated classifiers.',
            )
        else:
            result.add_pass(check_name)

    def check_license_classifier_mismatch(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that license classifiers match the LICENSE file content."""
        check_name = 'license_classifier_mismatch'
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            license_path = pkg.path / 'LICENSE'
            if not license_path.exists():
                continue
            try:
                license_text = license_path.read_text(encoding='utf-8')
            except OSError:
                continue

            # Detect license type from file content.
            detected_classifier: str = ''
            for pattern, classifier in _LICENSE_PATTERNS.items():
                if pattern.lower() in license_text.lower():
                    detected_classifier = classifier
                    break

            if not detected_classifier:
                continue

            # Check classifiers in pyproject.toml.
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            classifiers = project.get('classifiers', [])
            if not isinstance(classifiers, list):
                continue

            license_classifiers = [c for c in classifiers if isinstance(c, str) and c.startswith('License ::')]
            if not license_classifiers:
                continue

            # Check if any license classifier matches the detected license.
            if not any(detected_classifier in c for c in license_classifiers):
                issues.append(
                    f'{pkg.name}: LICENSE file looks like {detected_classifier.split("::")[-1].strip()}'
                    f' but classifiers say {", ".join(license_classifiers)}',
                )

        if issues:
            result.add_warning(
                check_name,
                f'License mismatch: {"; ".join(issues)}',
                hint='Ensure license classifiers in pyproject.toml match the LICENSE file.',
            )
        else:
            result.add_pass(check_name)

    def check_unreachable_extras(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that optional-dependencies reference known packages."""
        check_name = 'unreachable_extras'
        issues: list[str] = []

        # Build set of all known workspace package names.
        workspace_names = {pkg.name.lower().replace('-', '_').replace('.', '_') for pkg in packages}

        for pkg in packages:
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            optional_deps = project.get('optional-dependencies')
            if not isinstance(optional_deps, dict):
                continue

            for extra_name, deps in optional_deps.items():
                if not isinstance(deps, list):
                    continue
                for dep in deps:
                    if not isinstance(dep, str):
                        continue
                    # Skip self-referential extras like "mypackage[extra]".
                    dep_stripped = dep.strip()
                    if dep_stripped.startswith(pkg.name):
                        continue
                    match = _DEP_NAME_RE.match(dep_stripped)
                    if not match:
                        issues.append(f'{pkg.name}[{extra_name}]: unparseable dep {dep!r}')
                        continue
                    dep_name = match.group(1).lower().replace('-', '_').replace('.', '_')
                    # Only flag if it looks like a workspace package reference that doesn't exist.
                    # We can't check PyPI availability without network, so only check workspace.
                    # Skip common well-known packages.
                    if dep_name in workspace_names:
                        continue

        # This check only flags unparseable deps for now.
        # Full PyPI availability checking would require network access.
        if issues:
            result.add_warning(
                check_name,
                f'Unreachable extras: {"; ".join(issues)}',
                hint='Check that optional-dependencies reference valid package names.',
            )
        else:
            result.add_pass(check_name)

    def check_self_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that no package lists itself in its own dependencies."""
        check_name = 'self_dependencies'
        issues: list[str] = []

        for pkg in packages:
            doc = self._parse_pyproject(pkg)
            if doc is None:
                continue
            project = doc.get('project')
            if not isinstance(project, dict):
                continue
            deps = project.get('dependencies')
            if not isinstance(deps, list):
                continue

            pkg_norm = pkg.name.lower().replace('-', '_').replace('.', '_')
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                match = _DEP_NAME_RE.match(dep.strip())
                if not match:
                    continue
                dep_name = match.group(1).lower().replace('-', '_').replace('.', '_')
                if dep_name == pkg_norm:
                    issues.append(f'{pkg.name}: lists itself ({dep.strip()!r})')
                    break

        if issues:
            result.add_warning(
                check_name,
                f'Self-dependencies found: {"; ".join(issues)}',
                hint='Remove the package from its own [project].dependencies.',
            )
        else:
            result.add_pass(check_name)

    @staticmethod
    def _refresh_publishable(packages: list[Package]) -> None:
        """Re-read classifiers from disk and update ``is_publishable``."""
        _refresh_publishable(packages)

    def run_fixes(
        self,
        packages: list[Package],
        *,
        exclude_publish: list[str] | None = None,
        repo_owner: str = '',
        repo_name: str = '',
        namespace_dirs: list[str] | None = None,
        library_dirs: list[str] | None = None,
        plugin_dirs: list[str] | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Run all Python-specific auto-fixers.

        Returns a list of human-readable descriptions of changes made.
        """
        changes: list[str] = []

        # Metadata fixers.
        if exclude_publish:
            changes.extend(fix_publish_classifiers(packages, exclude_publish, dry_run=dry_run))
            # Refresh in-memory is_publishable after classifier changes.
            # fix_publish_classifiers modifies classifiers on disk but
            # the Package objects still hold the stale value. Without
            # this refresh, subsequent fixers that gate on is_publishable
            # (fix_readme_field, fix_changelog_url, etc.) would skip
            # packages that just became publishable.
            if not dry_run:
                _refresh_publishable(packages)
        changes.extend(fix_readme_field(packages, dry_run=dry_run))
        changes.extend(
            fix_changelog_url(
                packages,
                repo_owner=repo_owner,
                repo_name=repo_name,
                dry_run=dry_run,
            )
        )

        # Source tree fixers.
        changes.extend(fix_type_markers(packages, library_dirs=library_dirs, dry_run=dry_run))
        if namespace_dirs:
            changes.extend(
                fix_namespace_init(
                    packages,
                    namespace_dirs,
                    plugin_dirs=plugin_dirs,
                    dry_run=dry_run,
                )
            )

        # pyproject.toml fixers.
        changes.extend(fix_deprecated_classifiers(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        changes.extend(fix_requires_python(packages, dry_run=dry_run))
        changes.extend(fix_build_system(packages, dry_run=dry_run))
        changes.extend(fix_version_field(packages, dry_run=dry_run))
        changes.extend(fix_readme_content_type(packages, dry_run=dry_run))
        changes.extend(fix_placeholder_urls(packages, dry_run=dry_run))
        changes.extend(fix_license_classifier_mismatch(packages, dry_run=dry_run))
        changes.extend(fix_self_dependencies(packages, dry_run=dry_run))

        return changes
