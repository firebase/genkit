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

"""Shared types for the registry subpackage."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    'ChecksumResult',
]


@dataclass(frozen=True)
class ChecksumResult:
    """Result of checksum verification against a registry.

    Attributes:
        matched: Files where local and registry checksums agree.
        mismatched: Files where checksums differ.
            Maps filename to ``(local_sha, registry_sha)``.
        missing: Files not found on the registry.
    """

    matched: list[str] = field(default_factory=list)
    mismatched: dict[str, tuple[str, str]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True if all checksums match and none are missing."""
        return not self.mismatched and not self.missing

    def summary(self) -> str:
        """Return a human-readable summary."""
        parts: list[str] = []
        if self.matched:
            parts.append(f'{len(self.matched)} matched')
        if self.mismatched:
            parts.append(f'{len(self.mismatched)} mismatched')
        if self.missing:
            parts.append(f'{len(self.missing)} missing')
        return ', '.join(parts) if parts else 'no files checked'
