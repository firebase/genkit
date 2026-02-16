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

"""Validators for PEP 740 attestation and Security Insights structured output.

Provides validators that conform to the
:class:`~releasekit.backends.validation.Validator` protocol for:

- **PEP 740 Attestation** — validates the JSON structure of a
  ``.publish.attestation`` file against the PEP 740 schema.
- **Security Insights** — validates a ``SECURITY-INSIGHTS.yml`` dict
  against the OpenSSF Security Insights v2 schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from releasekit.backends.validation import ValidationResult


@dataclass(frozen=True)
class PEP740AttestationValidator:
    """Validates a PEP 740 attestation object structure.

    Checks that the attestation JSON conforms to the PEP 740 schema:
    ``version`` (must be 1), ``verification_material`` (with
    ``certificate`` and ``transparency_entries``), and ``envelope``
    (with ``statement`` and ``signature``).

    Attributes:
        validator_id: Override the default validator name.
    """

    validator_id: str = 'schema.pep740-attestation'

    @property
    def name(self) -> str:
        """Unique identifier for this validator."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate a PEP 740 attestation.

        Args:
            subject: A dict, JSON string, or :class:`~pathlib.Path`
                to a ``.publish.attestation`` file.

        Returns:
            A :class:`ValidationResult`.
        """
        data, err = _normalise_input(self.name, subject)
        if err is not None:
            return err

        assert data is not None  # for type checker

        issues = self._structural_check(data)
        if issues:
            return ValidationResult.failed(
                self.name,
                f'{len(issues)} structural issue(s)',
                hint='Fix the PEP 740 attestation to include all required fields.',
                details={'errors': issues},
            )

        return ValidationResult.passed(
            self.name,
            'PEP 740 attestation structure is valid',
        )

    @staticmethod
    def _structural_check(data: dict[str, Any]) -> list[str]:
        """Check PEP 740 attestation structure."""
        issues: list[str] = []

        # version must be 1.
        version = data.get('version')
        if version != 1:
            issues.append(f'version must be 1, got {version!r}')

        # verification_material.
        vm = data.get('verification_material')
        if not isinstance(vm, dict):
            issues.append('Missing or invalid "verification_material"')
        else:
            if 'certificate' not in vm:
                issues.append('verification_material missing "certificate"')
            entries = vm.get('transparency_entries')
            if not isinstance(entries, list) or len(entries) == 0:
                issues.append('verification_material.transparency_entries must be a non-empty array')

        # envelope.
        envelope = data.get('envelope')
        if not isinstance(envelope, dict):
            issues.append('Missing or invalid "envelope"')
        else:
            if 'statement' not in envelope:
                issues.append('envelope missing "statement"')
            if 'signature' not in envelope:
                issues.append('envelope missing "signature"')

        return issues


@dataclass(frozen=True)
class SecurityInsightsValidator:
    """Validates a Security Insights v2 document structure.

    Checks that the YAML/dict conforms to the OpenSSF Security
    Insights v2 schema: ``header`` (with ``schema-version``,
    ``last-updated``, ``last-reviewed``), ``project`` (with ``name``,
    ``administrators``, ``repositories``, ``vulnerability-reporting``),
    and ``repository`` (with ``url``, ``status``, ``core-team``,
    ``license``, ``security``).

    Attributes:
        validator_id: Override the default validator name.
    """

    validator_id: str = 'schema.security-insights'

    @property
    def name(self) -> str:
        """Unique identifier for this validator."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate a Security Insights document.

        Args:
            subject: A dict, JSON/YAML string, or :class:`~pathlib.Path`
                to a ``SECURITY-INSIGHTS.yml`` file.

        Returns:
            A :class:`ValidationResult`.
        """
        data, err = _normalise_input(self.name, subject)
        if err is not None:
            return err

        assert data is not None  # for type checker

        issues = self._structural_check(data)
        if issues:
            return ValidationResult.failed(
                self.name,
                f'{len(issues)} structural issue(s)',
                hint='Fix the Security Insights file to include all required fields.',
                details={'errors': issues},
            )

        return ValidationResult.passed(
            self.name,
            'Security Insights v2 structure is valid',
        )

    @staticmethod
    def _structural_check(data: dict[str, Any]) -> list[str]:
        """Check Security Insights v2 structure."""
        issues: list[str] = []

        # Header.
        header = data.get('header')
        if not isinstance(header, dict):
            issues.append('Missing or invalid "header"')
        else:
            if not header.get('schema-version'):
                issues.append('header missing "schema-version"')
            if not header.get('last-updated'):
                issues.append('header missing "last-updated"')
            if not header.get('last-reviewed'):
                issues.append('header missing "last-reviewed"')

        # Project.
        project = data.get('project')
        if not isinstance(project, dict):
            issues.append('Missing or invalid "project"')
        else:
            if not project.get('name'):
                issues.append('project missing "name"')
            admins = project.get('administrators')
            if not isinstance(admins, list) or len(admins) == 0:
                issues.append('project.administrators must be a non-empty array')
            repos = project.get('repositories')
            if not isinstance(repos, list) or len(repos) == 0:
                issues.append('project.repositories must be a non-empty array')
            else:
                for i, repo in enumerate(repos):
                    if not isinstance(repo, dict):
                        issues.append(f'project.repositories[{i}] must be an object')
                        continue
                    if not repo.get('name'):
                        issues.append(f'project.repositories[{i}] missing "name"')
                    if not repo.get('url'):
                        issues.append(f'project.repositories[{i}] missing "url"')
            vuln = project.get('vulnerability-reporting')
            if not isinstance(vuln, dict):
                issues.append('project missing "vulnerability-reporting"')
            else:
                if 'reports-accepted' not in vuln:
                    issues.append('vulnerability-reporting missing "reports-accepted"')
                if 'bug-bounty-available' not in vuln:
                    issues.append('vulnerability-reporting missing "bug-bounty-available"')

        # Repository.
        repository = data.get('repository')
        if not isinstance(repository, dict):
            issues.append('Missing or invalid "repository"')
        else:
            if not repository.get('url'):
                issues.append('repository missing "url"')
            if not repository.get('status'):
                issues.append('repository missing "status"')
            if 'accepts-change-request' not in repository:
                issues.append('repository missing "accepts-change-request"')
            if 'accepts-automated-change-request' not in repository:
                issues.append('repository missing "accepts-automated-change-request"')
            core_team = repository.get('core-team')
            if not isinstance(core_team, list) or len(core_team) == 0:
                issues.append('repository.core-team must be a non-empty array')
            lic = repository.get('license')
            if not isinstance(lic, dict):
                issues.append('repository missing "license"')
            else:
                if not lic.get('expression'):
                    issues.append('repository.license missing "expression"')
            security = repository.get('security')
            if not isinstance(security, dict):
                issues.append('repository missing "security"')
            else:
                assessments = security.get('assessments')
                if not isinstance(assessments, dict):
                    issues.append('repository.security missing "assessments"')

        return issues


def _normalise_input(
    validator_name: str,
    subject: Any,  # noqa: ANN401
) -> tuple[dict[str, Any] | None, ValidationResult | None]:
    """Normalise input to a dict, handling str, Path, and dict.

    Returns:
        A tuple of (data, error). If error is not None, data is None.
    """
    if isinstance(subject, dict):
        return subject, None

    if isinstance(subject, Path):
        if not subject.exists():
            return None, ValidationResult.failed(
                validator_name,
                f'File not found: {subject}',
            )
        raw = subject.read_text(encoding='utf-8')
    elif isinstance(subject, str):
        raw = subject
    else:
        return None, ValidationResult.failed(
            validator_name,
            f'Unsupported subject type: {type(subject).__name__}',
            hint='Pass a dict, JSON string, or Path.',
        )

    # Try JSON first, then YAML.
    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        pass

    try:
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data, None
        return None, ValidationResult.failed(
            validator_name,
            f'Expected a mapping, got {type(data).__name__}',
        )
    except ImportError:
        return None, ValidationResult.failed(
            validator_name,
            'Cannot parse YAML (PyYAML not installed) and input is not valid JSON',
        )
    except Exception as exc:  # noqa: BLE001
        return None, ValidationResult.failed(
            validator_name,
            f'Parse error: {exc}',
        )


__all__ = [
    'PEP740AttestationValidator',
    'SecurityInsightsValidator',
]
