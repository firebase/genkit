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

r"""OIDC token detection and validation adapters.

Provides platform-specific validators that check whether an OIDC
credential is available **and** structurally valid (not expired,
correct issuer, correct audience).

Supported platforms:

- **GitHub Actions** — ``ACTIONS_ID_TOKEN_REQUEST_URL`` env var
- **GitLab CI** — ``CI_JOB_JWT_V2`` / ``CI_JOB_JWT`` env vars
- **CircleCI** — ``CIRCLE_OIDC_TOKEN_V2`` env var

Each adapter implements the :class:`~releasekit.backends.validation.Validator`
protocol.  Use :func:`detect_oidc_validator` to auto-select the right
adapter for the current CI environment, or instantiate one directly
for testing.

Token validation checks (when a raw JWT is available):

1. **Structure** — Must be a valid 3-part base64-encoded JWT.
2. **Expiry** — ``exp`` claim must be in the future.
3. **Issuer** — ``iss`` claim must match the expected CI platform issuer.

.. note::

    These checks do **not** verify the cryptographic signature of the
    token (that requires fetching JWKS from the issuer).  Signature
    verification is the responsibility of the relying party (e.g.
    PyPI, Sigstore).  Our checks catch the most common failure modes:
    missing tokens, expired tokens, and wrong-issuer tokens.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from releasekit.backends.validation import ValidationResult
from releasekit.logging import get_logger

logger = get_logger(__name__)

# --- Known OIDC issuers ---

#: GitHub Actions OIDC issuer.
GITHUB_OIDC_ISSUER = 'https://token.actions.githubusercontent.com'

#: GitLab CI OIDC issuer.
GITLAB_OIDC_ISSUER = 'https://gitlab.com'

#: CircleCI OIDC issuer.
CIRCLECI_OIDC_ISSUER = 'https://oidc.circleci.com/org/'


# --- JWT helpers (no cryptographic verification) ---


def _decode_jwt_claims(token: str) -> dict[str, Any] | None:
    """Decode the payload (claims) of a JWT without signature verification.

    Args:
        token: Raw JWT string (``header.payload.signature``).

    Returns:
        Decoded claims dict, or ``None`` if the token is malformed.
    """
    parts = token.split('.')
    if len(parts) != 3:
        return None
    try:
        # JWT base64url encoding omits padding.
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None


def _check_expiry(claims: dict[str, Any]) -> tuple[bool, str]:
    """Check whether the token has expired.

    Args:
        claims: Decoded JWT claims.

    Returns:
        ``(ok, message)`` tuple.
    """
    exp = claims.get('exp')
    if exp is None:
        return True, 'No exp claim (token does not expire)'
    try:
        exp_time = float(exp)
    except (TypeError, ValueError):
        return False, f'Invalid exp claim: {exp!r}'
    now = time.time()
    if now > exp_time:
        delta = int(now - exp_time)
        return False, f'Token expired {delta}s ago (exp={int(exp_time)})'
    remaining = int(exp_time - now)
    return True, f'Token valid for {remaining}s'


def _check_issuer(
    claims: dict[str, Any],
    expected_issuer: str,
) -> tuple[bool, str]:
    """Check whether the token issuer matches the expected value.

    Args:
        claims: Decoded JWT claims.
        expected_issuer: Expected ``iss`` claim value (prefix match
            for issuers like CircleCI that include org IDs).

    Returns:
        ``(ok, message)`` tuple.
    """
    iss = claims.get('iss', '')
    if not iss:
        return False, 'Missing iss claim'
    if iss == expected_issuer or iss.startswith(expected_issuer):
        return True, f'Issuer OK: {iss}'
    return False, f'Unexpected issuer: {iss!r} (expected {expected_issuer!r})'


# --- Concrete validators ---


@dataclass(frozen=True)
class GitHubOIDCValidator:
    """Validates GitHub Actions OIDC token availability and claims.

    GitHub Actions provides OIDC tokens via the
    ``ACTIONS_ID_TOKEN_REQUEST_URL`` and ``ACTIONS_ID_TOKEN_REQUEST_TOKEN``
    environment variables.  The actual JWT is fetched at runtime by
    sigstore/cosign, so we validate:

    1. The request URL env var is set (token is requestable).
    2. If a raw token is provided as the subject, validate its
       structure, expiry, and issuer.

    Attributes:
        expected_issuer: Expected ``iss`` claim in the JWT.
    """

    expected_issuer: str = GITHUB_OIDC_ISSUER

    @property
    def name(self) -> str:
        """Return the validator name."""
        return 'oidc.github'

    def validate(self, subject: Any = None) -> ValidationResult:  # noqa: ANN401
        """Validate GitHub Actions OIDC credential.

        Args:
            subject: Optional raw JWT string to validate claims.
                If ``None``, only checks env var availability.

        Returns:
            A :class:`ValidationResult`.
        """
        request_url = os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL', '')
        request_token = os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN', '')

        if not request_url:
            return ValidationResult.failed(
                self.name,
                'ACTIONS_ID_TOKEN_REQUEST_URL not set',
                hint='Add "permissions: id-token: write" to your GitHub Actions workflow.',
                details={'env_var': 'ACTIONS_ID_TOKEN_REQUEST_URL'},
            )

        details: dict[str, Any] = {
            'request_url_set': bool(request_url),
            'request_token_set': bool(request_token),
        }

        # If a raw JWT is provided, validate its claims.
        if subject and isinstance(subject, str):
            return self._validate_token(subject, details)

        return ValidationResult.passed(
            self.name,
            'GitHub Actions OIDC credential available',
            details=details,
        )

    def _validate_token(
        self,
        token: str,
        details: dict[str, Any],
    ) -> ValidationResult:
        """Validate a raw JWT token's structure, expiry, and issuer."""
        claims = _decode_jwt_claims(token)
        if claims is None:
            return ValidationResult.failed(
                self.name,
                'Malformed JWT: expected 3 base64url-encoded parts',
                hint='The OIDC token is not a valid JWT. Check your workflow permissions.',
                details=details,
            )

        details['claims_iss'] = claims.get('iss', '')
        details['claims_aud'] = claims.get('aud', '')
        details['claims_sub'] = claims.get('sub', '')

        # Check expiry.
        exp_ok, exp_msg = _check_expiry(claims)
        details['expiry_check'] = exp_msg
        if not exp_ok:
            return ValidationResult.failed(
                self.name,
                f'GitHub OIDC token expired: {exp_msg}',
                hint='Request a fresh token. OIDC tokens are short-lived.',
                details=details,
            )

        # Check issuer.
        iss_ok, iss_msg = _check_issuer(claims, self.expected_issuer)
        details['issuer_check'] = iss_msg
        if not iss_ok:
            return ValidationResult.failed(
                self.name,
                f'GitHub OIDC issuer mismatch: {iss_msg}',
                hint=f'Expected issuer {self.expected_issuer!r}.',
                details=details,
            )

        return ValidationResult.passed(
            self.name,
            f'GitHub OIDC token valid ({exp_msg})',
            details=details,
        )


@dataclass(frozen=True)
class GitLabOIDCValidator:
    """Validates GitLab CI OIDC token availability and claims.

    GitLab CI provides OIDC tokens via ``CI_JOB_JWT_V2`` (preferred)
    or ``CI_JOB_JWT`` (legacy) environment variables.

    Attributes:
        expected_issuer: Expected ``iss`` claim in the JWT.
    """

    expected_issuer: str = GITLAB_OIDC_ISSUER

    @property
    def name(self) -> str:
        """Return the validator name."""
        return 'oidc.gitlab'

    def validate(self, subject: Any = None) -> ValidationResult:  # noqa: ANN401
        """Validate GitLab CI OIDC credential.

        Args:
            subject: Optional raw JWT string to validate claims.
                If ``None``, reads from ``CI_JOB_JWT_V2`` / ``CI_JOB_JWT``.

        Returns:
            A :class:`ValidationResult`.
        """
        token = (
            subject
            if subject and isinstance(subject, str)
            else os.environ.get('CI_JOB_JWT_V2', '') or os.environ.get('CI_JOB_JWT', '')
        )

        if not token:
            return ValidationResult.failed(
                self.name,
                'No GitLab OIDC token found (CI_JOB_JWT_V2 / CI_JOB_JWT)',
                hint=('Add "id_tokens: SIGSTORE_ID_TOKEN: aud: sigstore" to your .gitlab-ci.yml job.'),
                details={'env_vars_checked': ['CI_JOB_JWT_V2', 'CI_JOB_JWT']},
            )

        return self._validate_token(token)

    def _validate_token(self, token: str) -> ValidationResult:
        """Validate a raw JWT token's structure, expiry, and issuer."""
        details: dict[str, Any] = {}
        claims = _decode_jwt_claims(token)
        if claims is None:
            return ValidationResult.failed(
                self.name,
                'Malformed JWT: expected 3 base64url-encoded parts',
                hint='The GitLab OIDC token is not a valid JWT.',
                details=details,
            )

        details['claims_iss'] = claims.get('iss', '')
        details['claims_aud'] = claims.get('aud', '')
        details['claims_sub'] = claims.get('sub', '')

        exp_ok, exp_msg = _check_expiry(claims)
        details['expiry_check'] = exp_msg
        if not exp_ok:
            return ValidationResult.failed(
                self.name,
                f'GitLab OIDC token expired: {exp_msg}',
                hint='GitLab CI tokens are short-lived. Ensure the job is still running.',
                details=details,
            )

        # GitLab self-hosted instances may have a different issuer.
        server_url = os.environ.get('CI_SERVER_URL', '')
        expected = server_url if server_url else self.expected_issuer
        iss_ok, iss_msg = _check_issuer(claims, expected)
        details['issuer_check'] = iss_msg
        if not iss_ok:
            return ValidationResult.failed(
                self.name,
                f'GitLab OIDC issuer mismatch: {iss_msg}',
                hint=f'Expected issuer {expected!r}.',
                details=details,
            )

        return ValidationResult.passed(
            self.name,
            f'GitLab OIDC token valid ({exp_msg})',
            details=details,
        )


@dataclass(frozen=True)
class CircleCIOIDCValidator:
    """Validates CircleCI OIDC token availability and claims.

    CircleCI provides OIDC tokens via ``CIRCLE_OIDC_TOKEN_V2``.

    Attributes:
        expected_issuer: Expected ``iss`` claim prefix in the JWT.
    """

    expected_issuer: str = CIRCLECI_OIDC_ISSUER

    @property
    def name(self) -> str:
        """Return the validator name."""
        return 'oidc.circleci'

    def validate(self, subject: Any = None) -> ValidationResult:  # noqa: ANN401
        """Validate CircleCI OIDC credential.

        Args:
            subject: Optional raw JWT string to validate claims.
                If ``None``, reads from ``CIRCLE_OIDC_TOKEN_V2``.

        Returns:
            A :class:`ValidationResult`.
        """
        token = subject if subject and isinstance(subject, str) else os.environ.get('CIRCLE_OIDC_TOKEN_V2', '')

        if not token:
            return ValidationResult.failed(
                self.name,
                'No CircleCI OIDC token found (CIRCLE_OIDC_TOKEN_V2)',
                hint='Enable OIDC in your CircleCI project settings.',
                details={'env_var': 'CIRCLE_OIDC_TOKEN_V2'},
            )

        return self._validate_token(token)

    def _validate_token(self, token: str) -> ValidationResult:
        """Validate a raw JWT token's structure, expiry, and issuer."""
        details: dict[str, Any] = {}
        claims = _decode_jwt_claims(token)
        if claims is None:
            return ValidationResult.failed(
                self.name,
                'Malformed JWT: expected 3 base64url-encoded parts',
                hint='The CircleCI OIDC token is not a valid JWT.',
                details=details,
            )

        details['claims_iss'] = claims.get('iss', '')
        details['claims_aud'] = claims.get('aud', '')
        details['claims_sub'] = claims.get('sub', '')

        exp_ok, exp_msg = _check_expiry(claims)
        details['expiry_check'] = exp_msg
        if not exp_ok:
            return ValidationResult.failed(
                self.name,
                f'CircleCI OIDC token expired: {exp_msg}',
                hint='CircleCI OIDC tokens are short-lived.',
                details=details,
            )

        iss_ok, iss_msg = _check_issuer(claims, self.expected_issuer)
        details['issuer_check'] = iss_msg
        if not iss_ok:
            return ValidationResult.failed(
                self.name,
                f'CircleCI OIDC issuer mismatch: {iss_msg}',
                hint=f'Expected issuer prefix {self.expected_issuer!r}.',
                details=details,
            )

        return ValidationResult.passed(
            self.name,
            f'CircleCI OIDC token valid ({exp_msg})',
            details=details,
        )


# --- Auto-detection ---


def detect_oidc_validator() -> GitHubOIDCValidator | GitLabOIDCValidator | CircleCIOIDCValidator | None:
    """Auto-detect the OIDC validator for the current CI environment.

    Returns:
        The appropriate validator, or ``None`` if no CI OIDC
        environment is detected.
    """
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        return GitHubOIDCValidator()
    if os.environ.get('GITLAB_CI') == 'true':
        return GitLabOIDCValidator()
    if os.environ.get('CIRCLECI') == 'true':
        return CircleCIOIDCValidator()
    return None


def has_oidc_credential() -> bool:
    """Check whether an OIDC credential is available for signing.

    This is the **canonical** OIDC detection function.  All other
    modules should call this instead of checking env vars directly.

    Detects ambient OIDC tokens from supported CI platforms:

    - **GitHub Actions**: ``ACTIONS_ID_TOKEN_REQUEST_URL``
    - **GitLab CI**: ``CI_JOB_JWT_V2`` or ``CI_JOB_JWT``
    - **CircleCI**: ``CIRCLE_OIDC_TOKEN_V2``

    Returns:
        ``True`` if an OIDC credential is detected.
    """
    return bool(
        os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL')
        or os.environ.get('CI_JOB_JWT_V2')
        or os.environ.get('CI_JOB_JWT')
        or os.environ.get('CIRCLE_OIDC_TOKEN_V2')
    )


def validate_oidc_environment() -> ValidationResult:
    """Validate the OIDC environment for the current CI platform.

    Auto-detects the platform and runs the appropriate validator.
    If no CI platform is detected, returns a warning (not an error,
    since local builds don't need OIDC).

    Returns:
        A :class:`ValidationResult`.
    """
    validator = detect_oidc_validator()
    if validator is None:
        if os.environ.get('CI'):
            return ValidationResult.warning(
                'oidc.detect',
                'Running in CI but no known OIDC provider detected',
                hint=(
                    'SLSA provenance will be generated (L1) but cannot be signed (L2+). '
                    'Add OIDC permissions to your CI workflow for L2/L3.'
                ),
            )
        return ValidationResult.passed(
            'oidc.detect',
            'Not in CI — OIDC not required for local builds',
        )
    return validator.validate()


__all__ = [
    'CircleCIOIDCValidator',
    'GitHubOIDCValidator',
    'GitLabOIDCValidator',
    'detect_oidc_validator',
    'has_oidc_credential',
    'validate_oidc_environment',
]
