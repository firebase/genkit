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

"""CheckBackend protocol — the extension point for language-specific checks."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from releasekit.preflight import PreflightResult
from releasekit.workspace import Package


@runtime_checkable
class CheckBackend(Protocol):
    """Protocol for language-specific workspace checks.

    Each language/runtime implements this protocol to provide checks
    that are specific to its ecosystem. The methods receive the full
    package list and a :class:`PreflightResult` accumulator.

    Future implementations might include ``GoCheckBackend`` (checking
    for ``go.sum`` consistency, ``go vet`` compliance) or
    ``JsCheckBackend`` (checking for ``package.json`` completeness,
    ``@scope/`` naming conventions).

    A plugin system can compose multiple backends by calling each
    one's methods in sequence on the same :class:`PreflightResult`.
    """

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for language-specific type annotation markers.

        Examples: ``py.typed`` (Python PEP 561), ``d.ts`` (TypeScript),
        ``go vet`` (Go).
        """
        ...

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package versions follow ecosystem conventions.

        Examples: versions matching a core package (Python), workspace
        protocol versions (npm), module versions (Go).
        """
        ...

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package names follow ecosystem naming rules.

        Examples: ``{prefix}{dir}`` (Python), ``@scope/{dir}``
        (npm), ``module/{dir}`` (Go modules).
        """
        ...

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package metadata files are complete.

        Examples: ``pyproject.toml`` fields (Python), ``package.json``
        fields (npm), ``go.mod`` directives (Go).
        """
        ...

    def check_python_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages declare the same ``requires-python``.

        Mixed Python version requirements within a workspace cause
        install failures and CI matrix confusion.
        """
        ...

    def check_python_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have Python version classifiers.

        Missing classifiers cause PyPI to display incorrect Python
        version support information to users.
        """
        ...

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all dependencies resolve correctly.

        Runs the ecosystem's dependency checker (e.g. ``uv pip check``)
        to verify no missing or incompatible dependencies.
        """
        ...

    def check_namespace_init(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for accidental ``__init__.py`` in namespace directories.

        PEP 420 namespace packages must NOT have ``__init__.py``
        in intermediate namespace directories.
        An accidental ``__init__.py`` breaks import discovery for
        packages that contribute to the same namespace.
        """
        ...

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``readme`` in ``[project]``.

        Without this field, PyPI displays an empty page with no description,
        which gives a poor first impression to potential users.
        """
        ...

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have a ``Changelog`` entry in ``[project.urls]``.

        PyPI renders ``[project.urls]`` entries as sidebar links. A
        ``Changelog`` link is a widely expected convention that helps
        users track what changed between versions.
        """
        ...

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``Private :: Do Not Upload`` is consistent with ``exclude_publish``.

        Warns when a package is scheduled for publish but has the
        private classifier, or is excluded but lacks it.
        """
        ...

    def check_test_filename_collisions(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for test files with identical relative paths across packages.

        When two packages contain a test file at the same relative path,
        the test runner may silently shadow one depending on collection
        order and configuration.
        """
        ...

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that ``[build-system]`` is present and valid.

        A missing or misconfigured ``[build-system]`` causes pip to fall
        back to legacy ``setup.py`` behavior or fail entirely.
        """
        ...

    def check_version_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that ``[project].version`` is present or declared dynamic.

        Without either, the built package gets version ``0.0.0``.
        """
        ...

    def check_duplicate_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for duplicate entries in ``[project.dependencies]``.

        Duplicate dependencies with different specifiers cause resolver
        confusion and non-deterministic installs.
        """
        ...

    def check_pinned_deps_in_libraries(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that library packages don't pin dependencies with ``==``.

        Pinned dependencies in libraries break downstream users by
        preventing version resolution flexibility.
        """
        ...

    def check_requires_python(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``requires-python``.

        Without this, pip assumes any Python version works, leading to
        install failures on incompatible versions.
        """
        ...

    def check_readme_content_type(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that readme file extension matches content-type.

        A ``.md`` file with ``text/x-rst`` content-type (or vice versa)
        causes PyPI to render garbage.
        """
        ...

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package versions are PEP 440 compliant.

        Non-compliant versions are rejected by PyPI on upload.
        """
        ...

    def check_placeholder_urls(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for placeholder or empty URLs in ``[project.urls]``.

        URLs containing ``example.com`` or empty strings indicate
        unfinished metadata.
        """
        ...

    def check_legacy_setup_files(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for leftover ``setup.py`` or ``setup.cfg`` files.

        Dual-config packages are confusing and error-prone. Modern
        projects should use ``pyproject.toml`` exclusively.
        """
        ...

    def check_deprecated_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for deprecated trove classifiers.

        Deprecated classifiers may be rejected by PyPI or display
        incorrect information.
        """
        ...

    def check_license_classifier_mismatch(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that license classifiers match the LICENSE file content.

        A classifier saying MIT while the LICENSE file says Apache
        is confusing and potentially a legal issue.
        """
        ...

    def check_unreachable_extras(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that ``[project.optional-dependencies]`` entries are resolvable.

        Extras referencing packages that don't exist on PyPI or in the
        workspace will fail on install.
        """
        ...

    def check_self_dependencies(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that no package lists itself in ``[project].dependencies``."""
        ...

    def check_typing_classifier(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for ``Typing :: Typed`` and ``License :: OSI Approved`` classifiers.

        Missing ``Typing :: Typed`` prevents type-checker discovery of
        inline stubs.  Missing ``License :: OSI Approved`` reduces PyPI
        discoverability via license filters.
        """
        ...

    def check_keywords_and_urls(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have ``keywords`` and ``[project.urls]``.

        PyPI uses keywords for search ranking and renders
        ``[project.urls]`` as sidebar links.
        """
        ...

    def check_distro_deps(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that distro packaging deps are in sync with ``pyproject.toml``.

        Compares Debian/Ubuntu ``control`` and Fedora/RHEL ``.spec``
        dependency lists against ``[project].dependencies``.
        """
        ...

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
        """Run all language-specific auto-fixers.

        Returns a list of human-readable descriptions of changes made.
        Universal fixers (README, LICENSE, stale artifacts) are **not**
        included here — they are called separately by the CLI.
        """
        ...
