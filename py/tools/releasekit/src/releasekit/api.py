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

"""Programmatic Python API for releasekit.

Provides a high-level, importable API for using releasekit from Python
scripts, CI pipelines, and custom tooling — without going through the
CLI. Inspired by Nx Release's Node.js programmatic API.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ReleaseKit              │ The main entry point. Create one, call      │
    │                         │ methods like ``plan()``, ``publish()``.     │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ReleaseResult           │ A structured result from any operation,     │
    │                         │ with ``ok``, ``versions``, ``errors``.     │
    └─────────────────────────┴─────────────────────────────────────────────┘

Usage::

    from releasekit.api import ReleaseKit

    rk = ReleaseKit('/path/to/repo')

    # Preview version bumps
    result = await rk.plan()
    for v in result.versions:
        print(f'{v.name}: {v.old_version} → {v.new_version}')

    # Publish with options
    result = await rk.publish(dry_run=True, force=True)
    assert result.ok

    # Generate changelogs
    result = await rk.changelog()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.vcs import GitCLIBackend
from releasekit.changelog import generate_changelog, render_changelog, write_changelog
from releasekit.config import ReleaseConfig, WorkspaceConfig, build_package_configs, load_config
from releasekit.graph import build_graph, topo_sort
from releasekit.logging import get_logger
from releasekit.tags import format_tag
from releasekit.utils.date import utc_today
from releasekit.versioning import compute_bumps
from releasekit.versions import PackageVersion
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)


@dataclass
class ReleaseResult:
    """Result of a releasekit API operation.

    Attributes:
        ok: Whether the operation succeeded.
        versions: Computed version bumps.
        packages: Discovered packages.
        errors: Mapping of step → error message.
        metadata: Additional operation-specific data.
    """

    ok: bool = True
    versions: list[PackageVersion] = field(default_factory=list)
    packages: list[Package] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable summary."""
        bumped = [v for v in self.versions if not v.skipped]
        if self.ok:
            return f'{len(bumped)} packages to release'
        return f'Failed: {len(self.errors)} errors'


class ReleaseKit:
    """High-level programmatic API for releasekit.

    Provides methods for the core release workflow: discover packages,
    compute version bumps, generate changelogs, and publish.

    Args:
        workspace_root: Path to the workspace root (containing
            ``releasekit.toml``).
        workspace_label: Optional workspace label to target. If not
            specified, uses the first configured workspace.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        workspace_label: str = '',
    ) -> None:
        """Initialize with the workspace root and optional label."""
        self._root = Path(workspace_root).resolve()
        self._label = workspace_label
        self._config: ReleaseConfig | None = None
        self._ws_config: WorkspaceConfig | None = None

    @property
    def config(self) -> ReleaseConfig:
        """Loaded release configuration (lazy)."""
        if self._config is None:
            self._config = load_config(self._root)
        return self._config

    @property
    def ws_config(self) -> WorkspaceConfig:
        """Resolved workspace configuration (lazy)."""
        wsc = self._ws_config
        if wsc is None:
            if self._label and self._label in self.config.workspaces:
                wsc = self.config.workspaces[self._label]
            elif self.config.workspaces:
                wsc = next(iter(self.config.workspaces.values()))
            else:
                wsc = WorkspaceConfig()
            self._ws_config = wsc
        return wsc

    @property
    def effective_root(self) -> Path:
        """Effective workspace root (config root + workspace root offset)."""
        return (self._root / self.ws_config.root).resolve()

    def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all packages in the workspace.

        Args:
            exclude_patterns: Override exclude patterns (default: from config).

        Returns:
            List of discovered packages.
        """
        patterns = exclude_patterns if exclude_patterns is not None else self.ws_config.exclude
        return discover_packages(
            self.effective_root,
            exclude_patterns=patterns,
            ecosystem=self.ws_config.ecosystem or 'python',
        )

    async def plan(
        self,
        *,
        force_unchanged: bool = False,
        prerelease: str = '',
    ) -> ReleaseResult:
        """Compute version bumps without making any changes.

        Args:
            force_unchanged: Include packages with no changes.
            prerelease: Pre-release label (e.g. ``"rc"``).

        Returns:
            :class:`ReleaseResult` with computed versions.
        """
        try:
            packages = self.discover()
            vcs = GitCLIBackend(self._root)
            graph = build_graph(packages)
            propagate_graph = graph if (self.ws_config.propagate_bumps and not self.ws_config.synchronize) else None

            pkg_configs = build_package_configs(self.ws_config, [p.name for p in packages])
            versions = await compute_bumps(
                packages,
                vcs,
                tag_format=self.ws_config.tag_format,
                prerelease=prerelease,
                force_unchanged=force_unchanged,
                graph=propagate_graph,
                synchronize=self.ws_config.synchronize,
                major_on_zero=self.ws_config.major_on_zero,
                max_commits=self.ws_config.max_commits,
                bootstrap_sha=self.ws_config.bootstrap_sha,
                versioning_scheme=self.ws_config.versioning_scheme,
                package_configs=pkg_configs,
            )

            return ReleaseResult(
                ok=True,
                versions=versions,
                packages=packages,
            )
        except Exception as exc:
            return ReleaseResult(
                ok=False,
                errors={'plan': str(exc)},
            )

    async def changelog(
        self,
        *,
        dry_run: bool = False,
    ) -> ReleaseResult:
        """Generate changelogs for all packages.

        Args:
            dry_run: Preview without writing files.

        Returns:
            :class:`ReleaseResult` with metadata about written files.
        """
        try:
            packages = self.discover()
            vcs = GitCLIBackend(self._root)
            today = utc_today()
            written = 0
            skipped = 0

            for pkg in packages:
                tag = format_tag(
                    self.ws_config.tag_format,
                    name=pkg.name,
                    version=pkg.version,
                    label=self.ws_config.label,
                )
                tag_exists = await vcs.tag_exists(tag)
                since_tag = tag if tag_exists else None

                cl = await generate_changelog(
                    vcs=vcs,
                    version=pkg.version,
                    since_tag=since_tag,
                    paths=[str(pkg.path)],
                    date=today,
                )

                if not cl.sections:
                    skipped += 1
                    continue

                rendered = render_changelog(cl)
                changelog_path = pkg.path / 'CHANGELOG.md'
                if write_changelog(changelog_path, rendered, dry_run=dry_run):
                    written += 1
                else:
                    skipped += 1

            return ReleaseResult(
                ok=True,
                packages=packages,
                metadata={'written': written, 'skipped': skipped},
            )
        except Exception as exc:
            return ReleaseResult(
                ok=False,
                errors={'changelog': str(exc)},
            )

    async def version(self) -> ReleaseResult:
        """Show computed version bumps (alias for plan)."""
        return await self.plan()

    def graph(self) -> dict[str, list[str]]:
        """Return the dependency graph as an adjacency dict.

        Returns:
            Mapping of package name → list of dependency names.
        """
        packages = self.discover()
        graph = build_graph(packages)
        return dict(graph.edges)

    def topo_order(self) -> list[list[str]]:
        """Return packages in topological order (levels).

        Returns:
            List of levels, each a list of package names that can
            be processed in parallel.
        """
        packages = self.discover()
        graph = build_graph(packages)
        levels = topo_sort(graph)
        return [[pkg.name for pkg in level] for level in levels]


__all__ = [
    'ReleaseKit',
    'ReleaseResult',
]
