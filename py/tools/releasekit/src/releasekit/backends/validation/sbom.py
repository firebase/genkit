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

"""SBOM validation adapters (CycloneDX 1.5 and SPDX 2.3).

Validates SBOM documents against their official JSON Schemas using the
:class:`~releasekit.backends.validation.Validator` protocol.

Each validator can load its schema from:

1. An explicit dict passed at construction time.
2. A file path to a ``.schema.json`` file.
3. A built-in lightweight structural check when ``jsonschema`` is not
   installed.

Usage::

    from releasekit.backends.validation.sbom import (
        CycloneDXSchemaValidator,
        SPDXSchemaValidator,
    )

    v = CycloneDXSchemaValidator.from_schema_file(Path('bom-1.5.schema.json'))
    result = v.validate(sbom_dict)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from releasekit.backends.validation import ValidationResult


def _validate_against_schema(
    validator_name: str,
    data: Any,  # noqa: ANN401
    schema: dict[str, Any],
) -> ValidationResult:
    """Validate data against a JSON Schema.

    Uses ``jsonschema`` if available, otherwise falls back to a
    lightweight structural check.

    Args:
        validator_name: Name for the :class:`ValidationResult`.
        data: Parsed JSON data (dict or list).
        schema: JSON Schema dict.

    Returns:
        A :class:`ValidationResult`.
    """
    try:
        # Pick the validator class matching the schema's $schema dialect.
        dialect = schema.get('$schema', '')
        if 'draft-07' in dialect or 'draft-7' in dialect:
            validator_cls = jsonschema.Draft7Validator
        elif 'draft-04' in dialect or 'draft-4' in dialect:
            validator_cls = jsonschema.Draft4Validator
        else:
            validator_cls = jsonschema.Draft202012Validator
        validator = validator_cls(schema)
        errors = sorted(
            validator.iter_errors(data),
            key=lambda e: list(e.absolute_path),
        )
        if not errors:
            return ValidationResult.passed(validator_name, 'Schema validation passed')
        error_msgs = [f'{".".join(str(p) for p in e.absolute_path) or "(root)"}: {e.message}' for e in errors]
        return ValidationResult.failed(
            validator_name,
            f'{len(errors)} schema violation(s)',
            hint='Fix the SBOM output to match the expected schema.',
            details={'errors': error_msgs},
        )
    except ImportError:
        # Fallback: lightweight structural check.
        if not isinstance(data, dict):
            return ValidationResult.failed(
                validator_name,
                f'Expected a JSON object, got {type(data).__name__}',
            )
        return ValidationResult.warning(
            validator_name,
            'Full schema validation skipped (jsonschema not installed)',
            hint='Install jsonschema for full SBOM schema validation.',
        )


def _normalise_input(
    validator_name: str,
    subject: Any,  # noqa: ANN401
) -> tuple[dict[str, Any] | None, ValidationResult | None]:
    """Normalise a subject to a dict, returning an error result if invalid.

    Args:
        validator_name: Name for error results.
        subject: A dict, JSON string, or :class:`~pathlib.Path`.

    Returns:
        ``(data, None)`` on success, or ``(None, error_result)`` on failure.
    """
    if isinstance(subject, Path):
        if not subject.exists():
            return None, ValidationResult.failed(
                validator_name,
                f'File not found: {subject}',
            )
        try:
            data = json.loads(subject.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as exc:
            return None, ValidationResult.failed(
                validator_name,
                f'Invalid JSON: {exc}',
            )
        return data, None
    if isinstance(subject, str):
        try:
            data = json.loads(subject)
        except json.JSONDecodeError as exc:
            return None, ValidationResult.failed(
                validator_name,
                f'Invalid JSON: {exc}',
            )
        return data, None
    if isinstance(subject, dict):
        return subject, None
    return None, ValidationResult.failed(
        validator_name,
        f'Unsupported subject type: {type(subject).__name__}',
        hint='Pass a dict, JSON string, or Path.',
    )


# ── CycloneDX ──


@dataclass(frozen=True)
class CycloneDXSchemaValidator:
    """Validates a CycloneDX 1.5 SBOM against the official JSON Schema.

    Attributes:
        schema: The CycloneDX JSON Schema dict. If empty, only
            lightweight structural checks are performed.
        validator_id: Override the default validator name.
    """

    schema: dict[str, Any] = field(default_factory=dict)
    validator_id: str = 'schema.cyclonedx'

    @staticmethod
    def from_schema_file(
        path: Path,
        *,
        validator_id: str = 'schema.cyclonedx',
    ) -> CycloneDXSchemaValidator:
        """Create a validator from a schema file.

        Args:
            path: Path to ``bom-1.5.schema.json``.
            validator_id: Override the default validator name.

        Returns:
            A :class:`CycloneDXSchemaValidator` with the loaded schema.
        """
        schema = json.loads(path.read_text(encoding='utf-8'))
        return CycloneDXSchemaValidator(schema=schema, validator_id=validator_id)

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate a CycloneDX SBOM document.

        Args:
            subject: A dict, JSON string, or :class:`~pathlib.Path`
                to a ``.cdx.json`` file.

        Returns:
            A :class:`ValidationResult`.
        """
        data, err = _normalise_input(self.name, subject)
        if err is not None:
            return err

        assert data is not None  # for type checker

        # Lightweight structural checks (always run).
        issues = self._structural_check(data)
        if issues:
            return ValidationResult.failed(
                self.name,
                f'{len(issues)} structural issue(s)',
                hint='Fix the CycloneDX SBOM to include required fields.',
                details={'errors': issues},
            )

        # Full schema validation if schema is available.
        if self.schema:
            return _validate_against_schema(self.name, data, self.schema)

        return ValidationResult.passed(
            self.name,
            'CycloneDX structural validation passed (no schema for full validation)',
        )

    @staticmethod
    def _structural_check(data: dict[str, Any]) -> list[str]:
        """Lightweight structural check for CycloneDX 1.5."""
        issues: list[str] = []
        if data.get('bomFormat') != 'CycloneDX':
            issues.append(f'bomFormat must be "CycloneDX", got {data.get("bomFormat")!r}')
        spec = data.get('specVersion', '')
        if not spec:
            issues.append('Missing required field "specVersion"')
        components = data.get('components')
        if components is not None and not isinstance(components, list):
            issues.append(f'components must be an array, got {type(components).__name__}')
        if isinstance(components, list):
            for i, comp in enumerate(components):
                if not isinstance(comp, dict):
                    issues.append(f'components[{i}] must be an object')
                    continue
                if 'type' not in comp:
                    issues.append(f'components[{i}] missing required field "type"')
                if 'name' not in comp:
                    issues.append(f'components[{i}] missing required field "name"')
        return issues


# ── SPDX ──


@dataclass(frozen=True)
class SPDXSchemaValidator:
    """Validates an SPDX 2.3 SBOM against the official JSON Schema.

    Attributes:
        schema: The SPDX JSON Schema dict. If empty, only
            lightweight structural checks are performed.
        validator_id: Override the default validator name.
    """

    schema: dict[str, Any] = field(default_factory=dict)
    validator_id: str = 'schema.spdx'

    @staticmethod
    def from_schema_file(
        path: Path,
        *,
        validator_id: str = 'schema.spdx',
    ) -> SPDXSchemaValidator:
        """Create a validator from a schema file.

        Args:
            path: Path to ``spdx-2.3.schema.json``.
            validator_id: Override the default validator name.

        Returns:
            A :class:`SPDXSchemaValidator` with the loaded schema.
        """
        schema = json.loads(path.read_text(encoding='utf-8'))
        return SPDXSchemaValidator(schema=schema, validator_id=validator_id)

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate an SPDX SBOM document.

        Args:
            subject: A dict, JSON string, or :class:`~pathlib.Path`
                to a ``.spdx.json`` file.

        Returns:
            A :class:`ValidationResult`.
        """
        data, err = _normalise_input(self.name, subject)
        if err is not None:
            return err

        assert data is not None  # for type checker

        # Lightweight structural checks (always run).
        issues = self._structural_check(data)
        if issues:
            return ValidationResult.failed(
                self.name,
                f'{len(issues)} structural issue(s)',
                hint='Fix the SPDX SBOM to include required fields.',
                details={'errors': issues},
            )

        # Full schema validation if schema is available.
        if self.schema:
            return _validate_against_schema(self.name, data, self.schema)

        return ValidationResult.passed(
            self.name,
            'SPDX structural validation passed (no schema for full validation)',
        )

    @staticmethod
    def _structural_check(data: dict[str, Any]) -> list[str]:
        """Lightweight structural check for SPDX 2.3."""
        issues: list[str] = []
        if not data.get('spdxVersion'):
            issues.append('Missing required field "spdxVersion"')
        if data.get('SPDXID') != 'SPDXRef-DOCUMENT':
            issues.append(f'SPDXID must be "SPDXRef-DOCUMENT", got {data.get("SPDXID")!r}')
        if not data.get('name'):
            issues.append('Missing required field "name"')
        if not data.get('documentNamespace'):
            issues.append('Missing required field "documentNamespace"')
        if not data.get('dataLicense'):
            issues.append('Missing required field "dataLicense"')
        creation = data.get('creationInfo')
        if not isinstance(creation, dict):
            issues.append('Missing or invalid "creationInfo"')
        elif not creation.get('created'):
            issues.append('creationInfo missing required field "created"')
        packages = data.get('packages')
        if packages is not None and not isinstance(packages, list):
            issues.append(f'packages must be an array, got {type(packages).__name__}')
        if isinstance(packages, list):
            for i, pkg in enumerate(packages):
                if not isinstance(pkg, dict):
                    issues.append(f'packages[{i}] must be an object')
                    continue
                if 'SPDXID' not in pkg:
                    issues.append(f'packages[{i}] missing required field "SPDXID"')
                if 'name' not in pkg:
                    issues.append(f'packages[{i}] missing required field "name"')
                if 'downloadLocation' not in pkg:
                    issues.append(f'packages[{i}] missing required field "downloadLocation"')
        return issues


__all__ = [
    'CycloneDXSchemaValidator',
    'SPDXSchemaValidator',
]
