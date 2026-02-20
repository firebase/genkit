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

"""Provenance digest verification adapter.

Wraps :func:`releasekit.provenance.verify_provenance` into the
:class:`~releasekit.backends.validation.Validator` protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from releasekit.backends.validation import ValidationResult
from releasekit.provenance import verify_provenance


@dataclass(frozen=True)
class ProvenanceDigestValidator:
    """Validates that artifact digests match a provenance statement.

    The subject must be a dict with keys:

    - ``artifact_path``: :class:`~pathlib.Path` to the artifact file.
    - ``provenance_path``: :class:`~pathlib.Path` to the ``.intoto.jsonl`` file.

    Attributes:
        validator_id: Override the default validator name.
    """

    validator_id: str = 'provenance.digest'

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate artifact-to-provenance digest match.

        Args:
            subject: A dict with ``artifact_path`` and
                ``provenance_path`` keys (both :class:`~pathlib.Path`).

        Returns:
            A :class:`ValidationResult`.
        """
        if not isinstance(subject, dict):
            return ValidationResult.failed(
                self.name,
                'Subject must be a dict with artifact_path and provenance_path',
                hint='Pass {"artifact_path": Path(...), "provenance_path": Path(...)}.',
            )

        artifact_path = subject.get('artifact_path')
        provenance_path = subject.get('provenance_path')

        if not isinstance(artifact_path, Path):
            return ValidationResult.failed(
                self.name,
                'Missing or invalid artifact_path',
                hint='Provide a Path object for artifact_path.',
            )
        if not isinstance(provenance_path, Path):
            return ValidationResult.failed(
                self.name,
                'Missing or invalid provenance_path',
                hint='Provide a Path object for provenance_path.',
            )

        ok, reason = verify_provenance(artifact_path, provenance_path)
        if ok:
            return ValidationResult.passed(
                self.name,
                f'Artifact digest verified: {artifact_path.name}',
                details={
                    'artifact': str(artifact_path),
                    'provenance': str(provenance_path),
                    'reason': reason,
                },
            )
        return ValidationResult.failed(
            self.name,
            f'Digest mismatch: {artifact_path.name}',
            hint='Rebuild the artifact or regenerate provenance.',
            details={
                'artifact': str(artifact_path),
                'provenance': str(provenance_path),
                'reason': reason,
            },
        )


__all__ = [
    'ProvenanceDigestValidator',
]
