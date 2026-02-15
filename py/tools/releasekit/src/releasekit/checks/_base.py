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

"""Base check backend with no-op defaults for all protocol methods.

Ecosystem-specific backends inherit from :class:`BaseCheckBackend` and
override only the checks that are relevant to their ecosystem.  Methods
that are not overridden automatically pass.
"""

from __future__ import annotations

from releasekit.preflight import PreflightResult, run_check, run_version_consistency_check
from releasekit.workspace import Package


class BaseCheckBackend:
    """Base implementation of the :class:`CheckBackend` protocol.

    Provides concrete implementations for universal checks that are
    identical across all ecosystems (duplicate dependencies, self
    dependencies, version field, version consistency).  All other
    methods record a pass by default.  Subclasses override individual
    methods to add ecosystem-specific logic.

    Subclasses should set ``_core_package`` and override
    ``_manifest_path`` to customise the universal checks.
    """

    _core_package: str = ''

    def _manifest_path(self, pkg: Package) -> str:
        """Return the manifest file path string for *pkg*.

        Subclasses override this to return the ecosystem-specific
        manifest (e.g. ``go.mod``, ``Cargo.toml``, ``package.json``).
        The default returns ``pkg.manifest_path``.
        """
        return str(pkg.manifest_path)

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('type_markers')

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages share the same version as the core package."""
        run_version_consistency_check(
            result,
            'version_consistency',
            packages,
            core_package=self._core_package,
            manifest_path_fn=self._manifest_path,
        )

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('naming_convention')

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('metadata_completeness')

    def check_python_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('python_version_consistency')

    def check_python_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('python_classifiers')

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('dependency_resolution')

    def check_namespace_init(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('namespace_init')

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('readme_field')

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('changelog_url')

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """No-op: pass."""
        result.add_pass('publish_classifier_consistency')

    def check_test_filename_collisions(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('test_filename_collisions')

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('build_system')

    def check_version_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages declare a version."""
        run_check(
            result,
            'version_field',
            packages,
            lambda pkg: [(pkg.name, self._manifest_path(pkg))] if not pkg.version or pkg.version == '0.0.0' else [],
            message='Missing or default version',
            hint='Declare a version in the package manifest.',
        )

    def check_duplicate_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for duplicate dependency declarations."""

        def _probe(pkg: Package) -> list[tuple[str, str]]:
            seen: set[str] = set()
            dupes: list[tuple[str, str]] = []
            for dep in pkg.all_deps:
                if dep in seen:
                    dupes.append((f'{pkg.name}: {dep}', self._manifest_path(pkg)))
                seen.add(dep)
            return dupes

        run_check(
            result,
            'duplicate_dependencies',
            packages,
            _probe,
            message='Duplicate deps',
            hint='Remove duplicate dependency declarations.',
            severity='warning',
        )

    def check_pinned_deps_in_libraries(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('pinned_deps_in_libraries')

    def check_requires_python(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('requires_python')

    def check_readme_content_type(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('readme_content_type')

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('version_pep440')

    def check_placeholder_urls(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('placeholder_urls')

    def check_legacy_setup_files(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('legacy_setup_files')

    def check_deprecated_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('deprecated_classifiers')

    def check_license_classifier_mismatch(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('license_classifier_mismatch')

    def check_unreachable_extras(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('unreachable_extras')

    def check_self_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that no package depends on itself."""
        run_check(
            result,
            'self_dependencies',
            packages,
            lambda pkg: [(pkg.name, self._manifest_path(pkg))] if pkg.name in pkg.internal_deps else [],
            message='Self-dependency',
            hint='A package cannot depend on itself.',
        )

    def check_distro_deps(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """No-op: pass."""
        result.add_pass('distro_deps')

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
        """No-op: no fixes."""
        return []
