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

"""SLSA Build Level compliance validator.

Assesses a provenance statement and/or :class:`~releasekit.provenance.BuildContext`
against the SLSA Build track requirements (L0–L3) defined in
https://slsa.dev/spec/v1.1/requirements.

The validator checks **both** the provenance document structure and the
build environment properties to determine the highest achievable level.

Usage::

    from releasekit.backends.validation.slsa import SLSALevelValidator
    from releasekit.provenance import BuildContext

    ctx = BuildContext.from_env()
    v = SLSALevelValidator(target_level=3)
    result = v.validate(ctx)
    # result.ok is True only if L3 is fully achievable.
    # result.details['achieved_level'] tells you what was actually reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from releasekit.backends.validation import ValidationResult
from releasekit.provenance import BuildContext


@dataclass(frozen=True)
class SLSALevelValidator:
    """Validates SLSA Build level compliance.

    The validator accepts either a
    :class:`~releasekit.provenance.BuildContext` or a provenance dict
    as the subject.

    - When given a ``BuildContext``, it checks the *environment*
      properties (CI platform, runner isolation, OIDC availability).
    - When given a provenance dict, it checks the *document* structure
      (required fields, builder ID, externalParameters completeness).

    Attributes:
        target_level: The SLSA Build level to validate against (1–3).
        validator_id: Override the default validator name.
    """

    target_level: int = 3
    validator_id: str = 'slsa.build-level'

    @property
    def name(self) -> str:
        """Return the validator name."""
        return self.validator_id

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate SLSA Build level compliance.

        Args:
            subject: A :class:`~releasekit.provenance.BuildContext` or
                a provenance statement dict.

        Returns:
            A :class:`ValidationResult`. ``ok`` is ``True`` only if the
            target level is fully achieved.
        """
        if isinstance(subject, BuildContext):
            return self._validate_context(subject)
        if isinstance(subject, dict):
            return self._validate_provenance(subject)
        return ValidationResult.failed(
            self.name,
            f'Unsupported subject type: {type(subject).__name__}',
            hint='Pass a BuildContext or provenance dict.',
        )

    # ── BuildContext validation ──

    def _validate_context(self, ctx: Any) -> ValidationResult:  # noqa: ANN401
        """Validate build environment against SLSA requirements."""
        issues: list[str] = []
        achieved = int(ctx.slsa_build_level)

        # L1: provenance exists — always true if we're running.
        # L2 checks.
        if self.target_level >= 2:
            if not ctx.is_ci:
                issues.append('L2 requires a hosted build platform (currently local build)')
            if not ctx.builder_id:
                issues.append('L2 requires builder_id to be set')
            if not ctx.source_repo:
                issues.append('L2 requires source_repo for provenance authenticity')
            if not ctx.source_digest:
                issues.append('L2 requires source_digest (git commit SHA)')

        # L3 checks.
        if self.target_level >= 3:
            if not ctx.runner_environment:
                issues.append('L3 requires runner_environment to be known')
            elif ctx.ci_platform == 'github-actions':
                if ctx.runner_environment != 'github-hosted':
                    issues.append(f'L3 requires github-hosted runners (got {ctx.runner_environment!r})')
            if not ctx.source_entry_point:
                issues.append('L3 requires source_entry_point (build-as-code: build config must be in version control)')
            if not ctx.invocation_id:
                issues.append('L3 requires invocation_id for build traceability')
            if not ctx.source_ref:
                issues.append('L3 requires source_ref for complete externalParameters')

        if issues:
            return ValidationResult.failed(
                self.name,
                f'SLSA Build L{self.target_level} not achieved (reached L{achieved}): {len(issues)} issue(s)',
                hint=f'Fix the listed issues to reach Build L{self.target_level}.',
                details={
                    'target_level': self.target_level,
                    'achieved_level': achieved,
                    'issues': issues,
                },
            )

        return ValidationResult.passed(
            self.name,
            f'SLSA Build L{achieved} compliance verified',
            details={
                'target_level': self.target_level,
                'achieved_level': achieved,
            },
        )

    # ── Provenance document validation ──

    def _validate_provenance(self, stmt: dict[str, Any]) -> ValidationResult:
        """Validate provenance document structure for SLSA compliance."""
        issues: list[str] = []

        # L1: basic structure.
        predicate = stmt.get('predicate', {})
        if not isinstance(predicate, dict):
            return ValidationResult.failed(
                self.name,
                'Missing or invalid predicate',
            )

        bd = predicate.get('buildDefinition', {})
        rd = predicate.get('runDetails', {})

        if not bd.get('buildType'):
            issues.append('L1: missing buildDefinition.buildType')
        if 'externalParameters' not in bd:
            issues.append('L1: missing buildDefinition.externalParameters')
        builder = rd.get('builder', {})
        if not builder.get('id'):
            issues.append('L1: missing runDetails.builder.id')

        subjects = stmt.get('subject', [])
        if not subjects:
            issues.append('L1: subject list is empty')
        else:
            for i, s in enumerate(subjects):
                if not isinstance(s, dict):
                    issues.append(f'L1: subject[{i}] is not an object')
                    continue
                if not s.get('digest', {}).get('sha256'):
                    issues.append(f'L1: subject[{i}] missing sha256 digest')

        # L2: authenticity — builder.id must be a URI, version should exist.
        if self.target_level >= 2:
            bid = builder.get('id', '')
            if bid and not (bid.startswith('https://') or bid.startswith('local://')):
                issues.append(f'L2: builder.id should be a URI (got {bid!r})')
            if not builder.get('version'):
                issues.append('L2: builder.version should be populated for provenance authenticity')

        # L3: completeness and accuracy.
        if self.target_level >= 3:
            ext = bd.get('externalParameters', {})
            if not ext.get('repository'):
                issues.append('L3: externalParameters.repository is required (complete external parameters)')
            if not ext.get('ref'):
                issues.append('L3: externalParameters.ref is required (complete external parameters)')

            # resolvedDependencies should include source.
            deps = bd.get('resolvedDependencies', [])
            has_source_dep = any(d.get('digest', {}).get('gitCommit') for d in deps)
            if not has_source_dep:
                issues.append('L3: resolvedDependencies should include source with gitCommit digest')

            # builder.version should have runner details.
            version = builder.get('version', {})
            if not version.get('runnerEnvironment'):
                issues.append('L3: builder.version.runnerEnvironment is required for isolation verification')

            # internalParameters should record slsaBuildLevel.
            internal = bd.get('internalParameters', {})
            recorded_level = internal.get('slsaBuildLevel')
            if recorded_level is None:
                issues.append('L3: internalParameters.slsaBuildLevel should be recorded for compliance tracking')
            elif recorded_level < 3:
                issues.append(f'L3: recorded slsaBuildLevel is {recorded_level}, expected >= 3')

            # metadata should have invocationId.
            metadata = rd.get('metadata', {})
            if not metadata.get('invocationId'):
                issues.append('L3: metadata.invocationId is required for build traceability')

        # Determine achieved level from issues.
        achieved = self.target_level
        for issue in issues:
            if issue.startswith('L1:'):
                achieved = min(achieved, 0)
            elif issue.startswith('L2:'):
                achieved = min(achieved, 1)
            elif issue.startswith('L3:'):
                achieved = min(achieved, 2)

        if issues:
            return ValidationResult.failed(
                self.name,
                f'SLSA Build L{self.target_level} not achieved (reached L{achieved}): {len(issues)} issue(s)',
                hint=f'Fix the listed issues to reach Build L{self.target_level}.',
                details={
                    'target_level': self.target_level,
                    'achieved_level': achieved,
                    'issues': issues,
                },
            )

        return ValidationResult.passed(
            self.name,
            f'SLSA Build L{self.target_level} provenance compliance verified',
            details={
                'target_level': self.target_level,
                'achieved_level': self.target_level,
            },
        )


__all__ = [
    'SLSALevelValidator',
]
