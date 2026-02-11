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

"""Multi-ecosystem detection for releasekit.

Scans a monorepo to identify which package ecosystems are present
and instantiates the appropriate :class:`Workspace` backend for each.

Detection Signals::

    ┌─────────────────────────────────────────────────────────────────┐
    │  Ecosystem   │  Marker file                    │  Workspace    │
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  python/uv   │  pyproject.toml with            │  UvWorkspace  │
    │              │  [tool.uv.workspace]            │               │
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  js/pnpm     │  pnpm-workspace.yaml            │  PnpmWorkspace│
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  go          │  go.work                        │  (future)     │
    └──────────────┴─────────────────────────────────┴───────────────┘

Discovery Strategy::

    1. Walk up from CWD to find the monorepo root (contains .git).
    2. Scan the monorepo root for ecosystem markers at depth 0 and 1.
    3. Return a list of detected ecosystems with workspace instances.

    monorepo/
    ├── .git/                     ← monorepo root
    ├── releasekit.toml           ← root config
    ├── py/
    │   └── pyproject.toml        ← [tool.uv.workspace] → python
    ├── js/
    │   └── pnpm-workspace.yaml   ← pnpm workspace → js
    └── go/
        └── go.work               ← go workspace → go (future)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import unique
from pathlib import Path

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from releasekit.backends.workspace import PnpmWorkspace, UvWorkspace, Workspace
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

log = get_logger(__name__)


@unique
class Ecosystem(StrEnum):
    """Supported ecosystem identifiers for ``--ecosystem`` filtering."""

    PYTHON = 'python'
    JS = 'js'
    GO = 'go'


@dataclass(frozen=True)
class DetectedEcosystem:
    """A detected ecosystem in the monorepo.

    Attributes:
        ecosystem: The ecosystem type (python, js, go).
        root: Absolute path to the ecosystem workspace root
            (e.g. ``/repo/py/`` for a uv workspace).
        workspace: The instantiated :class:`Workspace` backend
            for this ecosystem, or ``None`` if no backend is
            implemented yet (e.g. Go).
    """

    ecosystem: Ecosystem
    root: Path
    workspace: Workspace | None = None


def find_monorepo_root(start: Path | None = None) -> Path:
    """Find the monorepo root by walking up from ``start``.

    Looks for a directory containing ``.git``. This is the directory
    where ``releasekit.toml`` should live.

    Args:
        start: Starting directory (defaults to CWD).

    Returns:
        Absolute path to the monorepo root.

    Raises:
        ReleaseKitError: If no monorepo root is found.
    """
    cwd = (start or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / '.git').exists():
            return parent
    raise ReleaseKitError(
        E.WORKSPACE_NOT_FOUND,
        'Could not find a monorepo root (.git directory).',
        hint='Run this command from within a git repository.',
    )


def _is_uv_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a uv workspace root."""
    pyproject = directory / 'pyproject.toml'
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding='utf-8')
        return '[tool.uv.workspace]' in text
    except OSError:
        return False


def _is_pnpm_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a pnpm workspace root."""
    return (directory / 'pnpm-workspace.yaml').is_file()


def _is_go_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Go workspace root."""
    return (directory / 'go.work').is_file()


def detect_ecosystems(
    monorepo_root: Path,
    *,
    ecosystem_filter: Ecosystem | None = None,
) -> list[DetectedEcosystem]:
    """Detect all package ecosystems in a monorepo.

    Scans the monorepo root and its immediate subdirectories for
    ecosystem markers (uv workspace, pnpm-workspace.yaml, go.work).

    Args:
        monorepo_root: Path to the monorepo root (contains ``.git``).
        ecosystem_filter: If set, only return ecosystems matching this
            type. Useful for ``--ecosystem python`` CLI filtering.

    Returns:
        List of detected ecosystems, sorted by ecosystem name.
        Each entry includes the workspace root and an instantiated
        :class:`Workspace` backend (when available).
    """
    detected: list[DetectedEcosystem] = []
    monorepo_root = monorepo_root.resolve()

    # Check candidates: the monorepo root itself, plus all immediate
    # child directories. This covers both flat repos (workspace at root)
    # and nested repos (workspace in py/, js/, go/ subdirs).
    candidates = [monorepo_root]
    try:
        candidates.extend(
            sorted(child for child in monorepo_root.iterdir() if child.is_dir() and not child.name.startswith('.'))
        )
    except OSError:
        pass

    for candidate in candidates:
        if _is_uv_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.PYTHON,
                    root=candidate,
                    workspace=UvWorkspace(candidate),
                )
            )
        if _is_pnpm_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.JS,
                    root=candidate,
                    workspace=PnpmWorkspace(candidate),
                )
            )
        if _is_go_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.GO,
                    root=candidate,
                    workspace=None,  # Go backend not yet implemented
                )
            )

    # Deduplicate by root path (a directory could match multiple patterns,
    # but in practice each root maps to exactly one ecosystem).
    seen_roots: set[Path] = set()
    unique: list[DetectedEcosystem] = []
    for eco in detected:
        if eco.root not in seen_roots:
            seen_roots.add(eco.root)
            unique.append(eco)

    result = sorted(unique, key=lambda e: e.ecosystem.value)

    # Apply filter if requested.
    if ecosystem_filter is not None:
        result = [e for e in result if e.ecosystem == ecosystem_filter]

    if result:
        log.info(
            'detected_ecosystems',
            count=len(result),
            ecosystems=[{'type': e.ecosystem.value, 'root': str(e.root)} for e in result],
        )
    else:
        ecosystem_hint = f' matching --ecosystem={ecosystem_filter.value}' if ecosystem_filter else ''
        log.warning(
            'no_ecosystems_detected',
            monorepo_root=str(monorepo_root),
            hint=f'No workspace markers found{ecosystem_hint}. '
            'Expected pyproject.toml with [tool.uv.workspace], '
            'pnpm-workspace.yaml, or go.work.',
        )

    return result


__all__ = [
    'DetectedEcosystem',
    'Ecosystem',
    'detect_ecosystems',
    'find_monorepo_root',
]
