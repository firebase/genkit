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

"""Bazel package manager backend for releasekit.

The :class:`BazelBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``bazel`` CLI (``bazel build``, ``bazel run``, ``bazel test``).

Bazel is a polyglot build system. Publishing is done via ``bazel run``
on a publish target whose name varies by ecosystem:

- **java_export** / **kt_jvm_export** (rules_jvm_external):
  ``bazel run //path:target.publish``
- **npm_package** (rules_js):
  ``bazel run //path:target.publish``
- **py_wheel** (rules_python):
  ``bazel run //path:target.publish``
- **dart_pub_publish** (rules_dart):
  ``bazel run //path:dart_pub_publish``
- **oci_push** (rules_oci):
  ``bazel run //path:push``
- **mvn_deploy** (custom):
  ``bazel build //path:target`` then ``mvn deploy``
- **native_tool** (ecosystem-native):
  ``bazel build //path:target`` then ecosystem-native publish
- **custom**:
  ``bazel run //path:custom_publish_target``

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.

Configuration in ``releasekit.toml``::

    [workspace.java]
    ecosystem = 'java'
    tool = 'bazel'
    root = 'java'
    # publish_mode = "java_export"   # optional override
    # publish_target = "//pkg:deploy.publish"  # optional explicit target
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.bazel')

# Publish modes supported by the Bazel backend.
PUBLISH_MODES: frozenset[str] = frozenset({
    'custom',
    'dart_pub_publish',
    'java_export',
    'kt_jvm_export',
    'mvn_deploy',
    'native_tool',
    'npm_package',
    'oci_push',
    'py_wheel',
})

# Publish modes that use the ``.publish`` suffix convention.
_DOT_PUBLISH_MODES: frozenset[str] = frozenset({
    'java_export',
    'kt_jvm_export',
    'npm_package',
    'py_wheel',
})

# Default publish target names per mode (when no explicit target is set).
_MODE_TARGET_SUFFIX: dict[str, str] = {
    'dart_pub_publish': 'dart_pub_publish',
    'oci_push': 'push',
}


class BazelBackend:
    """Bazel :class:`~releasekit.backends.pm.PackageManager` implementation.

    Wraps ``bazel build``, ``bazel run``, and ``bazel test`` to provide
    build, publish, lock, version-bump, resolve-check, and smoke-test
    operations for any Bazel-managed project.

    Args:
        workspace_root: Path to the Bazel workspace root (contains
            ``MODULE.bazel`` or ``WORKSPACE``).
        publish_mode: How to publish artifacts. One of :data:`PUBLISH_MODES`.
            Defaults to ``"java_export"``.
        publish_target: Explicit Bazel target label for publishing
            (e.g. ``"//pkg:deploy.publish"``). Overrides the default
            target derivation from ``publish_mode``.
    """

    def __init__(
        self,
        workspace_root: Path,
        *,
        publish_mode: str = 'java_export',
        publish_target: str = '',
    ) -> None:
        """Initialize with the Bazel workspace root."""
        self._root = workspace_root
        self._publish_mode = publish_mode if publish_mode in PUBLISH_MODES else 'java_export'
        self._publish_target = publish_target

    @property
    def publish_mode(self) -> str:
        """Return the configured publish mode."""
        return self._publish_mode

    # PackageManager protocol

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build a Bazel target using ``bazel build``.

        The build target is derived from the package directory relative
        to the workspace root: ``/repo/java/core`` → ``//java/core:all``.

        Args:
            package_dir: Path to the package directory containing a
                ``BUILD`` or ``BUILD.bazel`` file.
            output_dir: Unused for Bazel (output goes to ``bazel-bin``).
            no_sources: Unused for Bazel.
            dry_run: Log the command without executing.
        """
        target = _package_label(self._root, package_dir)
        cmd = ['bazel', 'build', target]

        log.info('build', target=target)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        registry_url: str | None = None,
        dist_tag: str | None = None,
        publish_branch: str | None = None,
        provenance: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish a Bazel-built artifact via ``bazel run``.

        The publish command depends on ``publish_mode``:

        - ``java_export`` / ``kt_jvm_export``: ``bazel run //pkg:target.publish``
        - ``npm_package``: ``bazel run //pkg:target.publish``
        - ``py_wheel``: ``bazel run //pkg:target.publish``
        - ``dart_pub_publish``: ``bazel run //pkg:dart_pub_publish``
        - ``oci_push``: ``bazel run //pkg:push``
        - ``mvn_deploy``: ``bazel run //pkg:deploy``
        - ``native_tool``: ``bazel run //pkg:publish``
        - ``custom``: ``bazel run //pkg:publish``

        Args:
            dist_dir: Path to the package directory.
            check_url: Unused for Bazel.
            registry_url: Custom registry URL. Passed as ``--define``
                for targets that support it.
            dist_tag: npm dist-tag. Passed as ``--define=DIST_TAG=<tag>``
                for npm_package publish mode.
            publish_branch: Unused for Bazel.
            provenance: Unused for Bazel.
            dry_run: Log the command without executing.
        """
        if self._publish_target:
            target = self._publish_target
        else:
            target = self._derive_publish_target(dist_dir)

        cmd = ['bazel', 'run', target]

        # Mode-specific defines.
        if registry_url:
            cmd.extend(['--define', f'REGISTRY_URL={registry_url}'])
        if dist_tag and self._publish_mode == 'npm_package':
            cmd.extend(['--define', f'DIST_TAG={dist_tag}'])

        log.info(
            'publish',
            target=target,
            mode=self._publish_mode,
            dry_run=dry_run,
        )
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Run Bazel dependency resolution.

        Uses ``bazel mod tidy`` (Bzlmod) to update the lockfile, or
        ``bazel mod deps --lockfile_mode=error`` to verify it.

        For JVM projects using rules_jvm_external, runs
        ``bazel run @maven//:pin`` to re-pin Maven dependencies.

        Args:
            check_only: Verify the lockfile is up-to-date without
                modifying it.
            upgrade_package: Unused for Bazel (Bzlmod handles upgrades
                via ``MODULE.bazel`` edits).
            cwd: Working directory override.
            dry_run: Log the command without executing.
        """
        work_dir = cwd or self._root

        if self._publish_mode in ('java_export', 'kt_jvm_export', 'mvn_deploy'):
            # JVM: re-pin Maven deps.
            if check_only:
                cmd = ['bazel', 'mod', 'deps', '--lockfile_mode=error']
            else:
                cmd = ['bazel', 'run', '@maven//:pin']
        elif check_only:
            cmd = ['bazel', 'mod', 'deps', '--lockfile_mode=error']
        else:
            cmd = ['bazel', 'mod', 'tidy']

        log.info('lock', check_only=check_only, cwd=str(work_dir))
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=work_dir,
            dry_run=dry_run,
        )

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Bump the version for a Bazel-managed package.

        Bazel packages store versions in ``MODULE.bazel``
        (``version = "x.y.z"``), ``version.bzl``, or build rule
        attributes. The actual file rewrite is handled by the workspace
        backend's ``rewrite_version`` method. This returns a synthetic
        result indicating the version bump intent.

        Args:
            package_dir: Path to the package directory.
            new_version: New version string.
            dry_run: Log the command without executing.
        """
        log.info(
            'version_bump',
            package=package_dir.name,
            version=new_version,
        )
        return CommandResult(
            command=['bazel', 'version-bump', str(package_dir), new_version],
            return_code=0,
            stdout=f'Version {new_version} will be set by workspace backend.',
            stderr='',
            duration=0.0,
            dry_run=dry_run,
        )

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        registry_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a published artifact is resolvable.

        - Java/Kotlin: ``bazel run @maven//:pin`` with artifact coords.
        - Other: ``bazel fetch //...``

        Args:
            package_name: Artifact coordinates (e.g. ``com.example:core``).
            version: Expected version.
            registry_url: Custom registry URL.
            dry_run: Log the command without executing.
        """
        if self._publish_mode in ('java_export', 'kt_jvm_export', 'mvn_deploy'):
            cmd = [
                'bazel',
                'run',
                '@maven//:pin',
                '--',
                f'--artifact={package_name}:{version}',
            ]
        else:
            cmd = ['bazel', 'fetch', '//...']

        log.info('resolve_check', package=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a Bazel-built package via ``bazel test``.

        Args:
            package_name: Package name or Bazel target path.
            version: Version (logged but not used in the command).
            dry_run: Log the command without executing.
        """
        if ':' in package_name or '//' in package_name:
            target = package_name
        else:
            target = f'//{package_name}:all'

        cmd = ['bazel', 'test', target]

        log.info('smoke_test', package=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )

    # Private helpers

    def _derive_publish_target(self, package_dir: Path) -> str:
        """Derive the publish target label based on publish mode.

        Convention by mode:

        - ``.publish`` modes: ``//pkg:pkg.publish``
        - ``dart_pub_publish``: ``//pkg:dart_pub_publish``
        - ``oci_push``: ``//pkg:push``
        - ``mvn_deploy`` / ``native_tool`` / ``custom``: ``//pkg:publish``
        """
        rel = _relative_label(self._root, package_dir)
        pkg_name = package_dir.name

        if self._publish_mode in _DOT_PUBLISH_MODES:
            return f'{rel}:{pkg_name}.publish'

        suffix = _MODE_TARGET_SUFFIX.get(self._publish_mode, 'publish')
        return f'{rel}:{suffix}'


def _package_label(workspace_root: Path, package_dir: Path) -> str:
    """Derive ``//pkg:all`` from an absolute package directory."""
    rel = _relative_label(workspace_root, package_dir)
    return f'{rel}:all'


def _relative_label(workspace_root: Path, package_dir: Path) -> str:
    """Derive ``//pkg`` from an absolute package directory."""
    try:
        rel = package_dir.resolve().relative_to(workspace_root.resolve())
        return f'//{rel}'
    except ValueError:
        return f'//{package_dir.name}'


__all__ = [
    'BazelBackend',
    'PUBLISH_MODES',
]
