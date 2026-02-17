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

"""Workspace protocol for releasekit.

The :class:`Workspace` protocol defines the async interface for
discovering workspace members, classifying dependencies, and
rewriting versions. Implementations:

- :class:`~releasekit.backends.workspace.uv.UvWorkspace` — ``pyproject.toml`` + ``[tool.uv]``
- :class:`~releasekit.backends.workspace.pnpm.PnpmWorkspace` — ``pnpm-workspace.yaml`` + ``package.json``
- :class:`~releasekit.backends.workspace.go.GoWorkspace` — ``go.work`` + ``go.mod``
- :class:`~releasekit.backends.workspace.dart.DartWorkspace` — ``pubspec.yaml`` + ``melos.yaml``
- :class:`~releasekit.backends.workspace.maven.MavenWorkspace` — ``pom.xml`` / ``settings.gradle``
- :class:`~releasekit.backends.workspace.cargo.CargoWorkspace` — ``Cargo.toml`` + ``[workspace]``
- :class:`~releasekit.backends.workspace.bazel.BazelWorkspace` — ``MODULE.bazel`` / ``WORKSPACE`` + ``BUILD``
- :class:`~releasekit.backends.workspace.clojure.ClojureWorkspace` — ``deps.edn`` / ``project.clj``
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from releasekit._types import DetectedLicense as DetectedLicense
from releasekit.backends.workspace._types import Package as Package
from releasekit.backends.workspace.bazel import BazelWorkspace as BazelWorkspace
from releasekit.backends.workspace.cargo import CargoWorkspace as CargoWorkspace
from releasekit.backends.workspace.clojure import ClojureWorkspace as ClojureWorkspace
from releasekit.backends.workspace.dart import DartWorkspace as DartWorkspace
from releasekit.backends.workspace.go import GoWorkspace as GoWorkspace
from releasekit.backends.workspace.maven import MavenWorkspace as MavenWorkspace
from releasekit.backends.workspace.pnpm import PnpmWorkspace as PnpmWorkspace
from releasekit.backends.workspace.uv import UvWorkspace as UvWorkspace

__all__ = [
    'BazelWorkspace',
    'CargoWorkspace',
    'ClojureWorkspace',
    'DartWorkspace',
    'DetectedLicense',
    'GoWorkspace',
    'MavenWorkspace',
    'Package',
    'PnpmWorkspace',
    'UvWorkspace',
    'Workspace',
]


@runtime_checkable
class Workspace(Protocol):
    """Protocol for workspace discovery, manifest parsing, and version rewriting.

    Each ecosystem implementation knows how to:

    1. **Discover** workspace members from the workspace root.
    2. **Classify** dependencies as workspace-sourced (internal) or
       external (pinned to a registry).
    3. **Rewrite** version strings in manifest files.

    All methods are async to avoid blocking the event loop during
    file I/O operations.
    """

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all packages in the workspace.

        Args:
            exclude_patterns: Glob patterns to exclude packages by name.

        Returns:
            Sorted list of discovered packages.
        """
        ...

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the version in a package manifest.

        Args:
            manifest_path: Path to the manifest file.
            new_version: New version string.

        Returns:
            The old version string.
        """
        ...

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency's version constraint in a manifest.

        Args:
            manifest_path: Path to the manifest file.
            dep_name: Dependency name to update.
            new_version: New version to pin to (``==new_version``).
        """
        ...

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Detect the license of a package from its manifest files.

        Each ecosystem backend knows which manifest fields contain
        license information:

        - **Python**: ``pyproject.toml`` — PEP 639 ``license``,
          ``license.text``, or classifiers.
        - **JS/TS**: ``package.json`` — ``license`` field.
        - **Rust**: ``Cargo.toml`` — ``[package].license``.
        - **Java**: ``pom.xml`` — ``<licenses><license><name>``.
        - **Go/Dart**: Falls through to LICENSE file scanning.

        Backends that don't have a manifest-level license field should
        return a :class:`DetectedLicense` with ``found=False`` so the
        caller can fall back to LICENSE file content matching.

        Args:
            pkg_path: Path to the package root directory.
            pkg_name: Package name (for diagnostics).

        Returns:
            A :class:`DetectedLicense`. Check ``.found`` to see if
            detection succeeded.
        """
        ...
