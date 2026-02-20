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

"""Shared types for the workspace subpackage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    'Package',
]


@dataclass(frozen=True)
class Package:
    """A single package discovered in the workspace.

    Attributes:
        name: The package name (e.g. ``"genkit"``).
        version: The version string (e.g. ``"0.5.0"``).
        path: Absolute path to the package directory.
        manifest_path: Absolute path to the package's manifest file
            (``pyproject.toml``, ``package.json``, ``Cargo.toml``, etc).
        internal_deps: Names of workspace-sourced packages this package
            depends on. These participate in version propagation.
        external_deps: Names of external (registry) packages this
            package depends on. These do NOT participate in propagation.
        all_deps: All dependency specifiers as raw strings.
        is_publishable: Whether this package should be published.
            Packages marked private are excluded.
    """

    name: str
    version: str
    path: Path
    manifest_path: Path
    internal_deps: list[str] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    all_deps: list[str] = field(default_factory=list)
    is_publishable: bool = True
