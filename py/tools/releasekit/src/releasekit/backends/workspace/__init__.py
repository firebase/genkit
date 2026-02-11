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
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from releasekit.backends.workspace._types import Package as Package
from releasekit.backends.workspace.pnpm import PnpmWorkspace as PnpmWorkspace
from releasekit.backends.workspace.uv import UvWorkspace as UvWorkspace

__all__ = [
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
