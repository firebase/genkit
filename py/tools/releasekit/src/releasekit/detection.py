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
    │  go          │  go.work                        │  GoWorkspace  │
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  dart        │  pubspec.yaml + melos.yaml      │  DartWorkspace│
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  java        │  pom.xml / settings.gradle       │ MavenWorkspace│
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  kotlin      │  build.gradle.kts (Kotlin DSL)  │ MavenWorkspace│
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  clojure     │  project.clj / deps.edn         │ ClojureWS     │
    ├──────────────┼─────────────────────────────────┼───────────────┤
    │  rust        │  Cargo.toml with [workspace]    │ CargoWorkspace│
    └──────────────┴─────────────────────────────────┴───────────────┘

Discovery Strategy::

    1. Walk up from CWD to find the monorepo root (contains .git).
    2. Scan the monorepo root for ecosystem markers at depth 0 and 1.
    3. Return a list of detected ecosystems with workspace instances.

Detection is **directory-name-agnostic**: any directory containing the
right marker file is detected, regardless of its name. The example
below uses conventional names, but ``python/``, ``typescript/``,
``golang/``, ``flutter/``, ``jvm/``, ``rs/``, etc. all work equally::

    monorepo/
    ├── .git/                     ← monorepo root
    ├── releasekit.toml           ← root config
    ├── py/
    │   └── pyproject.toml        ← [tool.uv.workspace] → python
    ├── js/
    │   └── pnpm-workspace.yaml   ← pnpm workspace → js
    ├── go/
    │   └── go.work               ← go workspace → go
    ├── dart/
    │   └── pubspec.yaml          ← dart workspace → dart
    ├── java/                     ← tests may live in javatest/
    │   └── pom.xml               ← maven workspace → java
    ├── kotlin/ (or kt/)
    │   └── build.gradle.kts      ← gradle workspace → kotlin
    ├── clojure/
    │   └── project.clj           ← leiningen workspace → clojure
    └── rust/
        └── Cargo.toml            ← cargo workspace → rust
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import unique
from pathlib import Path

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

from releasekit.backends.workspace import (
    CargoWorkspace,
    ClojureWorkspace,
    DartWorkspace,
    GoWorkspace,
    MavenWorkspace,
    PnpmWorkspace,
    UvWorkspace,
    Workspace,
)
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

log = get_logger(__name__)


@unique
class Ecosystem(StrEnum):
    """Supported ecosystem identifiers for ``--ecosystem`` filtering."""

    PYTHON = 'python'
    JS = 'js'
    GO = 'go'
    DART = 'dart'
    JAVA = 'java'
    KOTLIN = 'kotlin'
    CLOJURE = 'clojure'
    RUST = 'rust'


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
    """Check if ``directory`` contains a Go workspace or module root.

    Detects both multi-module Go workspaces (``go.work``) and
    standalone Go modules (``go.mod`` without ``go.work``).
    """
    return (directory / 'go.work').is_file() or (directory / 'go.mod').is_file()


def _is_dart_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Dart workspace root.

    Detects Melos workspaces (``melos.yaml``) or standalone Dart
    packages (``pubspec.yaml`` without being a Flutter sub-package).
    """
    return (directory / 'melos.yaml').is_file() or (
        (directory / 'pubspec.yaml').is_file()
        and not (directory / 'go.mod').is_file()  # Not a Go module
        and not (directory / 'pom.xml').is_file()  # Not a Maven project
    )


def _is_java_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Java/Maven/Gradle workspace root.

    Detects Maven multi-module projects (``pom.xml`` with ``<modules>``)
    or Gradle multi-project builds (``settings.gradle``).
    """
    if (directory / 'settings.gradle').is_file() or (directory / 'settings.gradle.kts').is_file():
        return True
    pom = directory / 'pom.xml'
    if pom.is_file():
        try:
            text = pom.read_text(encoding='utf-8')
            return '<modules>' in text
        except OSError:
            return False
    return False


def _is_kotlin_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Kotlin/Gradle workspace root.

    Detects Kotlin projects by looking for ``build.gradle.kts`` (Kotlin
    DSL) that is **not** already detected as a Java workspace (i.e. no
    ``settings.gradle`` / ``pom.xml``).  A ``build.gradle.kts`` with a
    sibling ``settings.gradle.kts`` is the canonical Kotlin multi-project
    layout.
    """
    if (directory / 'settings.gradle.kts').is_file():
        # Check if Kotlin DSL is used (settings.gradle.kts is Kotlin-specific).
        build_kts = directory / 'build.gradle.kts'
        if build_kts.is_file():
            try:
                text = build_kts.read_text(encoding='utf-8')
                # Kotlin projects typically apply the kotlin plugin.
                if 'kotlin' in text.lower():
                    return True
            except OSError:
                pass
    return False


def _is_clojure_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Clojure workspace root.

    Detects Leiningen projects (``project.clj``) or tools.deps
    projects (``deps.edn``).
    """
    return (directory / 'project.clj').is_file() or (directory / 'deps.edn').is_file()


def _is_cargo_workspace(directory: Path) -> bool:
    """Check if ``directory`` contains a Cargo workspace root.

    Detects Rust workspaces by looking for ``Cargo.toml`` containing
    a ``[workspace]`` section.
    """
    cargo_toml = directory / 'Cargo.toml'
    if not cargo_toml.is_file():
        return False
    try:
        text = cargo_toml.read_text(encoding='utf-8')
        return '[workspace]' in text
    except OSError:
        return False


def _parse_gitmodules(monorepo_root: Path) -> set[str]:
    """Parse ``.gitmodules`` and return the set of submodule paths.

    Each entry in ``.gitmodules`` looks like::

        [submodule "vendor/lib"]
            path = vendor/lib
            url = https://github.com/...

    Args:
        monorepo_root: Path to the monorepo root.

    Returns:
        Set of relative path strings for each submodule.
    """
    gitmodules = monorepo_root / '.gitmodules'
    if not gitmodules.is_file():
        return set()
    try:
        text = gitmodules.read_text(encoding='utf-8')
    except OSError:
        return set()
    # Match lines like: path = vendor/lib
    return set(re.findall(r'^\s*path\s*=\s*(.+)$', text, re.MULTILINE))


def _is_submodule(directory: Path) -> bool:
    """Return True if ``directory`` is a git submodule.

    Git submodules have a ``.git`` *file* (not directory) that contains
    a ``gitdir:`` pointer to the parent repo's ``.git/modules/`` tree.
    """
    git_path = directory / '.git'
    return git_path.is_file()


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
    # Submodule directories are excluded — they have their own release
    # lifecycle and should not be auto-detected as workspaces.
    submodule_paths = _parse_gitmodules(monorepo_root)
    candidates = [monorepo_root]
    try:
        for child in sorted(monorepo_root.iterdir()):
            if not child.is_dir() or child.name.startswith('.'):
                continue
            # Skip git submodules (detected via .gitmodules or .git file).
            rel = child.relative_to(monorepo_root)
            if str(rel) in submodule_paths or _is_submodule(child):
                log.info(
                    'skipping_submodule',
                    path=str(rel),
                    message=f'Skipping submodule: {rel}',
                )
                continue
            candidates.append(child)
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
                    workspace=GoWorkspace(candidate),
                )
            )
        if _is_dart_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.DART,
                    root=candidate,
                    workspace=DartWorkspace(candidate),
                )
            )
        if _is_kotlin_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.KOTLIN,
                    root=candidate,
                    workspace=MavenWorkspace(candidate),
                )
            )
        elif _is_java_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.JAVA,
                    root=candidate,
                    workspace=MavenWorkspace(candidate),
                )
            )
        if _is_clojure_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.CLOJURE,
                    root=candidate,
                    workspace=ClojureWorkspace(candidate),
                )
            )
        if _is_cargo_workspace(candidate):
            detected.append(
                DetectedEcosystem(
                    ecosystem=Ecosystem.RUST,
                    root=candidate,
                    workspace=CargoWorkspace(candidate),
                )
            )

    # Deduplicate by (root, ecosystem) pair.  Two different ecosystems
    # at the same root are valid (e.g. pyproject.toml + pnpm-workspace.yaml
    # both at the monorepo root).
    seen: set[tuple[Path, Ecosystem]] = set()
    unique: list[DetectedEcosystem] = []
    for eco in detected:
        key = (eco.root, eco.ecosystem)
        if key not in seen:
            seen.add(key)
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
            'pnpm-workspace.yaml, go.work/go.mod, melos.yaml/pubspec.yaml, '
            'or pom.xml/settings.gradle(.kts), project.clj/deps.edn, '
            'or Cargo.toml with [workspace].',
        )

    return result


__all__ = [
    'DetectedEcosystem',
    'Ecosystem',
    'detect_ecosystems',
    'find_monorepo_root',
    '_is_submodule',
    '_parse_gitmodules',
]
