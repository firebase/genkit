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

"""Artifact validation runner.

Detects release artifacts (provenance, attestations, SBOMs,
SECURITY-INSIGHTS) and dispatches the appropriate validator for each.
Used by the ``releasekit validate`` CLI subcommand.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationEntry:
    """Result of validating a single artifact.

    Attributes:
        file: Artifact filename.
        validator: Name of the validator that ran.
        ok: Whether validation passed.
        status: Human-readable status string.
    """

    file: str
    validator: str
    ok: bool
    status: str


@dataclass
class ValidationReport:
    """Aggregated results from validating multiple artifacts.

    Attributes:
        entries: Individual validation results.
        failures: Count of failed validations.
    """

    entries: list[ValidationEntry] = field(default_factory=list)
    failures: int = 0

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the report to JSON."""
        records = [{'file': e.file, 'validator': e.validator, 'status': e.status} for e in self.entries]
        return json.dumps(records, indent=indent)

    def format_table(self) -> str:
        """Format the report as a human-readable table."""
        lines: list[str] = []
        lines.append(f'{"File":<50} {"Validator":<30} {"Status"}')
        lines.append('-' * 100)
        for e in self.entries:
            lines.append(f'{e.file:<50} {e.validator:<30} {e.status}')
        lines.append(
            f'\n{len(self.entries)} artifact(s) checked, {self.failures} failure(s).',
        )
        return '\n'.join(lines)


def detect_artifacts(workspace_root: Path) -> list[Path]:
    """Auto-detect release artifacts in a workspace.

    Searches for provenance, attestation, SECURITY-INSIGHTS, and SBOM
    files in standard locations.

    Args:
        workspace_root: Path to the workspace root.

    Returns:
        Sorted list of artifact paths found.
    """
    candidates = [
        *sorted(workspace_root.glob('provenance*.intoto.jsonl')),
        *sorted(workspace_root.glob('dist/*.publish.attestation')),
        *sorted(workspace_root.glob('SECURITY-INSIGHTS.yml')),
        *sorted(workspace_root.glob('SECURITY_INSIGHTS.yml')),
        *sorted(workspace_root.glob('.github/SECURITY-INSIGHTS.yml')),
        *sorted(workspace_root.glob('sbom*.json')),
        *sorted(workspace_root.glob('sbom*.xml')),
    ]
    return [p for p in candidates if p.is_file()]


def _run_one(artifact_path: Path, name: str) -> list[ValidationEntry]:
    """Run all matching validators against a single artifact.

    Args:
        artifact_path: Path to the artifact file.
        name: Filename for display.

    Returns:
        List of validation entries (one per validator matched).
    """
    entries: list[ValidationEntry] = []

    if 'provenance' in name and name.endswith('.intoto.jsonl'):
        entries.append(
            _try_validate(
                artifact_path,
                name,
                'releasekit.backends.validation.schema',
                'ProvenanceSchemaValidator',
                fallback_name='provenance',
            )
        )

    if name.endswith('.publish.attestation'):
        entries.append(
            _try_validate(
                artifact_path,
                name,
                'releasekit.backends.validation.attestation',
                'PEP740AttestationValidator',
                fallback_name='pep740',
            )
        )

    if 'security' in name.lower() and name.lower().endswith('.yml'):
        entries.append(
            _try_validate(
                artifact_path,
                name,
                'releasekit.backends.validation.attestation',
                'SecurityInsightsValidator',
                fallback_name='security-insights',
            )
        )

    if 'sbom' in name.lower() and (name.endswith('.json') or name.endswith('.xml')):
        entries.append(
            _try_validate(
                artifact_path,
                name,
                'releasekit.backends.validation.schema',
                'SBOMSchemaValidator',
                fallback_name='sbom',
            )
        )

    return entries


def _try_validate(
    artifact_path: Path,
    name: str,
    module_path: str,
    class_name: str,
    *,
    fallback_name: str,
) -> ValidationEntry:
    """Import a validator class and run it against an artifact.

    Args:
        artifact_path: Path to the artifact file.
        name: Filename for display.
        module_path: Dotted module path to import from.
        class_name: Validator class name within the module.
        fallback_name: Validator name to use if import fails.

    Returns:
        A single validation entry.
    """
    try:
        mod = importlib.import_module(module_path)
        validator_cls = getattr(mod, class_name)
        v = validator_cls()
        vr = v.validate(artifact_path)
        status = '\u2705 pass' if vr.ok else f'\u274c fail: {vr.message}'
        return ValidationEntry(file=name, validator=v.name, ok=vr.ok, status=status)
    except Exception as exc:  # noqa: BLE001
        return ValidationEntry(
            file=name,
            validator=fallback_name,
            ok=False,
            status=f'\u274c error: {exc}',
        )


def validate_artifacts(artifact_paths: list[Path]) -> ValidationReport:
    """Run all matching validators against a list of artifact paths.

    Args:
        artifact_paths: Paths to artifact files to validate.

    Returns:
        A :class:`ValidationReport` with all results.
    """
    report = ValidationReport()

    for artifact_path in artifact_paths:
        name = artifact_path.name
        entries = _run_one(artifact_path, name)

        if entries:
            for entry in entries:
                report.entries.append(entry)
                if not entry.ok:
                    report.failures += 1
        else:
            report.entries.append(
                ValidationEntry(
                    file=name,
                    validator='(none)',
                    ok=True,
                    status='\u2139\ufe0f  skipped (no matching validator)',
                )
            )

    return report


__all__ = [
    'ValidationEntry',
    'ValidationReport',
    'detect_artifacts',
    'validate_artifacts',
]
