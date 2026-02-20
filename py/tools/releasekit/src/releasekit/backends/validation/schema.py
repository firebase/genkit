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

"""JSON Schema validation adapters.

Wraps :func:`releasekit.provenance.validate_provenance_schema` and
any future schema validators into the :class:`Validator` protocol.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from releasekit.backends.validation import ValidationResult
from releasekit.provenance import validate_provenance_schema


@dataclass(frozen=True)
class ProvenanceSchemaValidator:
    """Validates a provenance statement against the SLSA Provenance v1 JSON Schema.

    Wraps :func:`releasekit.provenance.validate_provenance_schema`
    into the :class:`~releasekit.backends.validation.Validator` protocol.

    Attributes:
        validator_id: Override the default validator name.
    """

    validator_id: str = 'schema.provenance'

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate a provenance statement.

        Args:
            subject: A dict, JSON string, or :class:`~pathlib.Path`
                to a ``.intoto.jsonl`` file.

        Returns:
            A :class:`ValidationResult`.
        """
        errors = validate_provenance_schema(subject)
        if not errors:
            return ValidationResult.passed(
                self.name,
                'Provenance statement conforms to SLSA Provenance v1 schema',
            )
        return ValidationResult.failed(
            self.name,
            f'{len(errors)} schema violation(s)',
            hint='Fix the provenance output to match the SLSA Provenance v1 schema.',
            details={'errors': errors},
        )


@dataclass(frozen=True)
class JsonSchemaValidator:
    """Generic JSON Schema validator.

    Validates any JSON-serializable subject against a user-provided
    JSON Schema dict.  Useful for validating config files, SBOM
    documents, or any structured data.

    Attributes:
        schema: The JSON Schema dict to validate against.
        validator_id: Name for this validator instance.
    """

    schema: dict[str, Any] = field(default_factory=dict)
    validator_id: str = 'schema.generic'

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate a subject against the JSON Schema.

        Args:
            subject: A dict or JSON string to validate.

        Returns:
            A :class:`ValidationResult`.
        """
        if not self.schema:
            return ValidationResult.failed(
                self.name,
                'No schema configured',
                hint='Provide a JSON Schema dict when constructing the validator.',
            )

        # Normalise to dict.
        if isinstance(subject, (str, Path)):
            if isinstance(subject, Path):
                if not subject.exists():
                    return ValidationResult.failed(
                        self.name,
                        f'File not found: {subject}',
                    )
                raw = subject.read_text(encoding='utf-8')
            else:
                raw = subject
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                return ValidationResult.failed(
                    self.name,
                    f'Invalid JSON: {exc}',
                )
        else:
            data = subject

        # Try jsonschema first.
        try:
            validator = jsonschema.Draft202012Validator(self.schema)
            errors = sorted(
                validator.iter_errors(data),
                key=lambda e: list(e.absolute_path),
            )
            if not errors:
                return ValidationResult.passed(
                    self.name,
                    'Schema validation passed',
                )
            error_msgs = [f'{".".join(str(p) for p in e.absolute_path) or "(root)"}: {e.message}' for e in errors]
            return ValidationResult.failed(
                self.name,
                f'{len(errors)} schema violation(s)',
                hint='Fix the data to match the expected schema.',
                details={'errors': error_msgs},
            )
        except ImportError:
            # Fallback: just check it's a dict.
            if not isinstance(data, dict):
                return ValidationResult.failed(
                    self.name,
                    f'Expected a JSON object, got {type(data).__name__}',
                )
            return ValidationResult.passed(
                self.name,
                'Schema validation skipped (jsonschema not installed)',
            )


__all__ = [
    'JsonSchemaValidator',
    'ProvenanceSchemaValidator',
]
