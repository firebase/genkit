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

"""Maven/Gradle package manager backend for releasekit.

The :class:`MavenBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``mvn`` CLI (``mvn package``, ``mvn deploy``, etc.).

Also supports Gradle-based projects by detecting ``build.gradle``
and using ``./gradlew`` instead of ``mvn``.

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.maven')


class MavenBackend:
    """Java :class:`~releasekit.backends.pm.PackageManager` implementation.

    Supports both Maven (``pom.xml``) and Gradle (``build.gradle``)
    projects. Detects the build tool based on the presence of
    ``pom.xml`` or ``build.gradle`` in the package directory.

    Args:
        workspace_root: Path to the Java workspace root.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the workspace root path."""
        self._root = workspace_root

    @staticmethod
    def _is_gradle(package_dir: Path) -> bool:
        """Check if the package uses Gradle."""
        return (package_dir / 'build.gradle').is_file() or (package_dir / 'build.gradle.kts').is_file()

    @staticmethod
    def _gradle_cmd(package_dir: Path) -> str:
        """Return the Gradle wrapper command if available, else 'gradle'."""
        wrapper = package_dir / 'gradlew'
        if wrapper.is_file():
            return str(wrapper)
        return 'gradle'

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build a Java package using Maven or Gradle."""
        if self._is_gradle(package_dir):
            gradle = self._gradle_cmd(package_dir)
            cmd = [gradle, 'build', '-x', 'test']
        else:
            cmd = ['mvn', 'package', '-DskipTests']

        log.info('build', package=package_dir.name)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=package_dir,
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
        """Publish a Java package using Maven deploy or Gradle publish.

        Args:
            dist_dir: Path to the package directory.
            check_url: Ignored.
            registry_url: Custom Maven repository URL.  For Gradle projects
                this is passed as ``-PmavenUrl=<url>`` (the ``build.gradle``
                must read the property to configure the repository).
            dist_tag: Ignored (Maven has no dist-tag concept).
            publish_branch: Ignored.
            provenance: Ignored.
            dry_run: If True, logs the command without executing.
        """
        if self._is_gradle(dist_dir):
            gradle = self._gradle_cmd(dist_dir)
            cmd = [gradle, 'publish']
            if registry_url:
                cmd.append(f'-PmavenUrl={registry_url}')
        else:
            cmd = ['mvn', 'deploy', '-DskipTests']
            if registry_url:
                cmd.append(f'-DaltDeploymentRepository=releasekit::default::{registry_url}')

        log.info('publish', package=dist_dir.name, dry_run=dry_run)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=dist_dir,
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
        """Resolve dependencies using Maven or Gradle.

        Args:
            check_only: For Gradle, run ``dependencies`` without
                ``--refresh-dependencies`` (a read-only check).
                For Maven, run ``dependency:resolve`` either way.
            upgrade_package: Refresh a specific dependency.  For Gradle
                this is ignored (Gradle refreshes all or nothing).
                For Maven, this is ignored (Maven resolves all).
            cwd: Working directory.
            dry_run: Log the command without executing.
        """
        work_dir = cwd or self._root
        if self._is_gradle(work_dir):
            gradle = self._gradle_cmd(work_dir)
            if check_only:
                cmd = [gradle, 'dependencies']
            else:
                cmd = [gradle, 'dependencies', '--refresh-dependencies']
        else:
            cmd = ['mvn', 'dependency:resolve']

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
        """Bump version in ``pom.xml`` using Maven versions plugin.

        For Gradle projects, version bumping is handled by the workspace
        backend rewriting ``build.gradle`` directly.
        """
        if self._is_gradle(package_dir):
            log.info(
                'version_bump_gradle',
                package=package_dir.name,
                version=new_version,
                reason='Gradle version set via workspace backend.',
            )
            return CommandResult(
                command=['gradle', 'version-bump', new_version],
                return_code=0,
                stdout=f'Version {new_version} will be set in build.gradle.',
                stderr='',
                duration=0.0,
                dry_run=dry_run,
            )

        cmd = [
            'mvn',
            'versions:set',
            f'-DnewVersion={new_version}',
            '-DgenerateBackupPoms=false',
        ]

        log.info('version_bump', package=package_dir.name, version=new_version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=package_dir,
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
        """Verify a Maven/Gradle artifact is resolvable.

        For Maven, uses ``mvn dependency:get``.
        For Gradle, uses ``gradle dependencyInsight`` to query the
        dependency from the configured repositories.
        """
        if self._is_gradle(self._root):
            gradle = self._gradle_cmd(self._root)
            cmd = [
                gradle,
                'dependencyInsight',
                f'--dependency={package_name}',
            ]
        else:
            cmd = [
                'mvn',
                'dependency:get',
                f'-Dartifact={package_name}:{version}',
                '-Dtransitive=false',
            ]

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
        """Smoke-test a Maven/Gradle artifact by resolving it."""
        return await self.resolve_check(
            package_name,
            version,
            dry_run=dry_run,
        )


__all__ = [
    'MavenBackend',
]
