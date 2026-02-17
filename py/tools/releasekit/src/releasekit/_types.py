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

"""Shared leaf-level types used across releasekit.

This module must have **zero** imports from other ``releasekit``
subpackages to avoid circular-import chains.  It is safe to import
from any module in the project.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    'DetectedLicense',
]


@dataclass(frozen=True)
class DetectedLicense:
    """Result of extracting a license string from a manifest.

    Attributes:
        value: The raw license string as found in the manifest.
            Empty string if no license was detected.
        source: Where the license was found (e.g. ``"pyproject.toml"``,
            ``"package.json"``, ``"LICENSE"``).
        package_name: Name of the package (for diagnostics).
    """

    value: str
    source: str
    package_name: str

    @property
    def found(self) -> bool:
        """``True`` if a license string was detected."""
        return bool(self.value)
