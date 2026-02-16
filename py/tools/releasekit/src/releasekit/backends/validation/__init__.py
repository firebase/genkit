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

r"""Extensible validation framework for releasekit.

Provides a :class:`Validator` protocol that all validation backends
implement, and a :class:`ValidationResult` dataclass for uniform
reporting.  Concrete adapters live in sibling modules:

- :mod:`~.oidc` — OIDC token detection and claim validation
- :mod:`~.schema` — JSON Schema validation (provenance, config)
- :mod:`~.provenance` — Artifact-to-provenance digest verification

Architecture::

    ┌──────────────────────────────────────────────────────┐
    │                  Validator (Protocol)                 │
    │  validate(subject) → ValidationResult                │
    └──────────┬───────────┬───────────────┬───────────────┘
               │           │               │
    ┌──────────┴──┐ ┌──────┴──────┐ ┌──────┴──────────────┐
    │ OIDCToken   │ │ Schema      │ │ Provenance           │
    │ Validator   │ │ Validator   │ │ Validator            │
    │             │ │             │ │                      │
    │ ├ GitHub    │ │ ├ Provenance│ │ Verifies artifact    │
    │ ├ GitLab    │ │ └ Config    │ │ digests match        │
    │ └ CircleCI  │ │             │ │ provenance subjects  │
    └─────────────┘ └─────────────┘ └──────────────────────┘

Usage::

    from releasekit.backends.validation import (
        ValidationResult,
        Validator,
        run_validators,
    )

    results = run_validators([oidc_validator, schema_validator], subject)
    for r in results:
        if not r.ok:
            print(f'{r.validator_name}: {r.message}')
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a single validation check.

    Attributes:
        ok: ``True`` if the validation passed.
        validator_name: Identifier of the validator that produced this
            result (e.g. ``'oidc.github'``, ``'schema.provenance'``).
        message: Human-readable description of the outcome.
        hint: Actionable suggestion when ``ok`` is ``False``.
        details: Arbitrary key-value pairs with additional context
            (e.g. token claims, schema errors, digest mismatches).
        severity: ``'error'`` (blocks release), ``'warning'``
            (informational), or ``'info'`` (passed check detail).
    """

    ok: bool
    validator_name: str
    message: str = ''
    hint: str = ''
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = 'error'

    @staticmethod
    def passed(
        validator_name: str,
        message: str = 'OK',
        *,
        details: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Create a passing result."""
        return ValidationResult(
            ok=True,
            validator_name=validator_name,
            message=message,
            severity='info',
            details=details or {},
        )

    @staticmethod
    def failed(
        validator_name: str,
        message: str,
        *,
        hint: str = '',
        details: dict[str, Any] | None = None,
        severity: str = 'error',
    ) -> ValidationResult:
        """Create a failing result."""
        return ValidationResult(
            ok=False,
            validator_name=validator_name,
            message=message,
            hint=hint,
            severity=severity,
            details=details or {},
        )

    @staticmethod
    def warning(
        validator_name: str,
        message: str,
        *,
        hint: str = '',
        details: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Create a warning result (non-blocking)."""
        return ValidationResult(
            ok=True,
            validator_name=validator_name,
            message=message,
            hint=hint,
            severity='warning',
            details=details or {},
        )


@runtime_checkable
class Validator(Protocol):
    """Protocol for all validation backends.

    Each validator inspects a ``subject`` (which can be anything —
    a file path, a dict, a token string, etc.) and returns a
    :class:`ValidationResult`.

    Validators are composable: pass a list to :func:`run_validators`
    to execute them all and collect results.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this validator (e.g. ``'oidc.github'``)."""
        ...

    def validate(self, subject: Any) -> ValidationResult:  # noqa: ANN401
        """Validate the given subject.

        Args:
            subject: The object to validate. The type depends on the
                concrete validator (e.g. a token string for OIDC, a
                dict for schema validation, a Path for provenance).

        Returns:
            A :class:`ValidationResult` describing the outcome.
        """
        ...


def run_validators(
    validators: list[Validator],
    subject: Any,  # noqa: ANN401
) -> list[ValidationResult]:
    """Run multiple validators against the same subject.

    Args:
        validators: List of validators to execute.
        subject: The object to validate.

    Returns:
        List of :class:`ValidationResult`, one per validator.
    """
    return [v.validate(subject) for v in validators]


def all_passed(results: list[ValidationResult]) -> bool:
    """Return ``True`` if all results passed (no errors).

    Warning-severity results are considered passing.
    """
    return all(r.ok or r.severity == 'warning' for r in results)


def errors_only(results: list[ValidationResult]) -> list[ValidationResult]:
    """Filter to only error-severity failures."""
    return [r for r in results if not r.ok and r.severity == 'error']


def warnings_only(results: list[ValidationResult]) -> list[ValidationResult]:
    """Filter to only warning-severity results."""
    return [r for r in results if r.severity == 'warning']


__all__ = [
    'ValidationResult',
    'Validator',
    'all_passed',
    'errors_only',
    'run_validators',
    'warnings_only',
]
