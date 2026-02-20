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

r"""PEP 740 digital attestations for PyPI packages.

Generates, verifies, and fetches `PEP 740`_ attestations using the
``pypi-attestations`` library.  Attestations cryptographically bind a
distribution file (sdist or wheel) to a Sigstore identity (e.g. a
GitHub Actions workflow), enabling downstream consumers to verify that
a package was published by a specific Trusted Publisher.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ PEP 740             │ PyPI standard for digital attestations.       │
    │                     │ Each file gets a signed statement linking it  │
    │                     │ to the publisher's OIDC identity.             │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Attestation         │ A Sigstore-signed in-toto statement with the  │
    │                     │ distribution name + SHA-256 digest as subject.│
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Distribution        │ A Python sdist (.tar.gz) or wheel (.whl).    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Publisher           │ A Trusted Publisher identity (GitHub Actions, │
    │                     │ GitLab CI, Google Cloud).                     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Provenance          │ PEP 740 provenance object: one or more       │
    │                     │ attestation bundles for a distribution file.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Integrity API       │ PyPI endpoint to fetch provenance for a file:│
    │                     │ GET /integrity/<proj>/<ver>/<file>/provenance │
    └─────────────────────┴────────────────────────────────────────────────┘

Signing flow::

    sign_distribution(dist_path)
         │
         ├── Distribution.from_file(dist_path)
         ├── Obtain OIDC identity (ambient CI creds)
         ├── Attestation.sign(signer, dist)
         ├── Write .publish.attestation JSON
         └── Return AttestationResult(signed=True)

Verification flow::

    verify_attestation(dist_path, attestation_path, publisher=...)
         │
         ├── Distribution.from_file(dist_path)
         ├── Attestation.model_validate_json(...)
         ├── attestation.verify(identity=publisher, dist=dist)
         └── Return AttestationResult(verified=True)

Fetch flow::

    fetch_provenance("sampleproject", "4.0.0", "sampleproject-4.0.0.tar.gz")
         │
         ├── GET https://pypi.org/integrity/<proj>/<ver>/<file>/provenance
         ├── Parse Provenance object
         └── Return Provenance

.. _PEP 740: https://peps.python.org/pep-0740/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pypi_attestations import (
    Attestation,
    AttestationError,
    ConversionError,
    Distribution,
    GitHubPublisher,
    GitLabPublisher,
    GooglePublisher,
    Provenance,
    Publisher,
    VerificationError,
)
from sigstore.models import Bundle, ClientTrustConfig
from sigstore.oidc import IdentityToken, detect_credential
from sigstore.sign import SigningContext
from sigstore.verify import Verifier
from sigstore.verify.policy import UnsafeNoOp

from releasekit.logging import get_logger

logger = get_logger(__name__)

# PyPI Integrity API base URL.
DEFAULT_PYPI_URL = 'https://pypi.org'

# Timeout for PyPI Integrity API requests.
INTEGRITY_API_TIMEOUT = 30.0


@dataclass(frozen=True)
class AttestationResult:
    """Result of an attestation signing or verification operation.

    Attributes:
        dist_path: Path to the distribution file.
        attestation_path: Path to the ``.publish.attestation`` file.
        signed: Whether the attestation was successfully created.
        verified: Whether the attestation was successfully verified.
        predicate_type: The attestation predicate type (e.g.
            ``https://docs.pypi.org/attestations/publish/v1``).
        reason: Human-readable reason if the operation was skipped or failed.
    """

    dist_path: Path = field(default_factory=Path)
    attestation_path: Path = field(default_factory=Path)
    signed: bool = False
    verified: bool = False
    predicate_type: str = ''
    reason: str = ''


def sign_distribution(
    dist_path: Path,
    *,
    output_dir: Path | None = None,
    identity_token: str = '',
    dry_run: bool = False,
) -> AttestationResult:
    """Sign a Python distribution with a PEP 740 attestation.

    Creates a ``.publish.attestation`` file alongside the distribution.
    Uses ambient OIDC credentials (GitHub Actions, GitLab CI, Google
    Cloud) for Sigstore keyless signing.

    Args:
        dist_path: Path to the ``.tar.gz`` or ``.whl`` file.
        output_dir: Directory for the attestation file (defaults to
            the distribution's directory).
        identity_token: Explicit OIDC identity token. If empty,
            sigstore will attempt ambient credential detection.
        dry_run: If ``True``, report what would be signed without signing.

    Returns:
        An :class:`AttestationResult` with the outcome.
    """
    if not dist_path.exists():
        return AttestationResult(
            dist_path=dist_path,
            reason=f'Distribution not found: {dist_path}',
        )

    attest_dir = output_dir or dist_path.parent
    attest_path = attest_dir / f'{dist_path.name}.publish.attestation'

    if dry_run:
        logger.info(
            'attestation_dry_run',
            dist=str(dist_path),
            attestation=str(attest_path),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attest_path,
            reason='dry-run: would create PEP 740 attestation',
        )

    try:
        dist = Distribution.from_file(dist_path)

        # Obtain OIDC identity token.
        if identity_token:
            token = IdentityToken(identity_token)
        else:
            raw = detect_credential()
            if raw is None:
                return AttestationResult(
                    dist_path=dist_path,
                    attestation_path=attest_path,
                    reason=(
                        'No ambient OIDC credential detected. '
                        'PEP 740 attestations require a Trusted Publisher '
                        '(GitHub Actions, GitLab CI, or Google Cloud).'
                    ),
                )
            token = IdentityToken(raw)

        # Create signing context with production Sigstore infrastructure.
        trust_config = ClientTrustConfig.production()
        ctx = SigningContext.from_trust_config(trust_config)

        with ctx.signer(token) as signer:
            attestation = Attestation.sign(signer, dist)

        # Write the attestation.
        attest_dir.mkdir(parents=True, exist_ok=True)
        attest_path.write_text(
            attestation.model_dump_json(indent=2),
            encoding='utf-8',
        )

        logger.info(
            'attestation_created',
            dist=str(dist_path),
            attestation=str(attest_path),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attest_path,
            signed=True,
            predicate_type='https://docs.pypi.org/attestations/publish/v1',
        )
    except (AttestationError, ConversionError) as exc:
        logger.error(
            'attestation_sign_failed',
            dist=str(dist_path),
            error=str(exc),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attest_path,
            reason=f'Attestation signing failed: {exc}',
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'attestation_sign_error',
            dist=str(dist_path),
            error=str(exc),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attest_path,
            reason=f'Unexpected error during attestation signing: {exc}',
        )


def verify_attestation(
    dist_path: Path,
    attestation_path: Path,
    *,
    publisher: Publisher | None = None,
    staging: bool = False,
    offline: bool = False,
) -> AttestationResult:
    """Verify a PEP 740 attestation against a distribution.

    Args:
        dist_path: Path to the ``.tar.gz`` or ``.whl`` file.
        attestation_path: Path to the ``.publish.attestation`` file.
        publisher: Trusted Publisher identity to verify against.
            If ``None``, only the cryptographic signature is verified
            (not the publisher identity).
        staging: Use Sigstore staging infrastructure (for testing).
        offline: Skip TUF repository refresh (for air-gapped envs).

    Returns:
        An :class:`AttestationResult` with the outcome.
    """
    if not dist_path.exists():
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attestation_path,
            reason=f'Distribution not found: {dist_path}',
        )

    if not attestation_path.exists():
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attestation_path,
            reason=f'Attestation not found: {attestation_path}',
        )

    try:
        dist = Distribution.from_file(dist_path)
        attestation_json = attestation_path.read_bytes()
        attestation = Attestation.model_validate_json(attestation_json)

        if publisher is not None:
            predicate_type, _predicate = attestation.verify(
                identity=publisher,
                dist=dist,
                staging=staging,
                offline=offline,
            )
        else:
            # Verify signature only (no publisher identity check).
            # Use UnsafeNoOp policy via the Sigstore verifier directly.
            bundle = attestation.to_bundle()
            if staging:
                verifier = Verifier.staging(offline=offline)
            else:
                verifier = Verifier.production(offline=offline)

            verifier.verify_dsse(bundle, UnsafeNoOp())
            predicate_type = attestation.statement.get(
                'predicateType',
                '',
            )

        logger.info(
            'attestation_verified',
            dist=str(dist_path),
            attestation=str(attestation_path),
            predicate_type=predicate_type,
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attestation_path,
            verified=True,
            predicate_type=predicate_type,
        )
    except (VerificationError, ConversionError) as exc:
        logger.error(
            'attestation_verify_failed',
            dist=str(dist_path),
            error=str(exc),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attestation_path,
            reason=f'Attestation verification failed: {exc}',
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'attestation_verify_error',
            dist=str(dist_path),
            error=str(exc),
        )
        return AttestationResult(
            dist_path=dist_path,
            attestation_path=attestation_path,
            reason=f'Unexpected error during attestation verification: {exc}',
        )


def convert_bundle_to_attestation(
    bundle_path: Path,
    *,
    output_path: Path | None = None,
) -> AttestationResult:
    """Convert a Sigstore bundle to a PEP 740 attestation.

    Useful when you already have a ``.sigstore.json`` bundle from
    :func:`releasekit.signing.sign_artifact` and want to convert it
    to the PEP 740 format for PyPI upload.

    Args:
        bundle_path: Path to the ``.sigstore.json`` bundle.
        output_path: Path for the output attestation file. If ``None``,
            replaces ``.sigstore.json`` with ``.publish.attestation``.

    Returns:
        An :class:`AttestationResult` with the outcome.
    """
    if not bundle_path.exists():
        return AttestationResult(
            reason=f'Bundle not found: {bundle_path}',
        )

    if output_path is None:
        # foo.tar.gz.sigstore.json → foo.tar.gz.publish.attestation
        stem = bundle_path.name
        if stem.endswith('.sigstore.json'):
            stem = stem[: -len('.sigstore.json')]
        output_path = bundle_path.parent / f'{stem}.publish.attestation'

    try:
        bundle_json = bundle_path.read_bytes()
        bundle = Bundle.from_json(bundle_json)
        attestation = Attestation.from_bundle(bundle)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            attestation.model_dump_json(indent=2),
            encoding='utf-8',
        )

        logger.info(
            'bundle_converted',
            bundle=str(bundle_path),
            attestation=str(output_path),
        )
        return AttestationResult(
            attestation_path=output_path,
            signed=True,
            predicate_type='https://docs.pypi.org/attestations/publish/v1',
        )
    except ConversionError as exc:
        logger.error(
            'bundle_conversion_failed',
            bundle=str(bundle_path),
            error=str(exc),
        )
        return AttestationResult(
            reason=f'Bundle conversion failed: {exc}',
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'bundle_conversion_error',
            bundle=str(bundle_path),
            error=str(exc),
        )
        return AttestationResult(
            reason=f'Unexpected error during bundle conversion: {exc}',
        )


async def fetch_provenance(
    project: str,
    version: str,
    filename: str,
    *,
    pypi_url: str = DEFAULT_PYPI_URL,
    timeout: float = INTEGRITY_API_TIMEOUT,
) -> Provenance | None:
    """Fetch PEP 740 provenance for a distribution from PyPI.

    Uses the PyPI Integrity API:
    ``GET /integrity/<project>/<version>/<filename>/provenance``

    Args:
        project: PyPI project name (e.g. ``"sampleproject"``).
        version: Package version (e.g. ``"4.0.0"``).
        filename: Distribution filename (e.g.
            ``"sampleproject-4.0.0.tar.gz"``).
        pypi_url: Base URL for the PyPI instance.
        timeout: HTTP request timeout in seconds.

    Returns:
        A :class:`Provenance` object, or ``None`` if the file has no
        provenance (404) or the request fails.
    """
    url = f'{pypi_url}/integrity/{project}/{version}/{filename}/provenance'
    headers = {'Accept': 'application/vnd.pypi.integrity.v1+json'}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 404:
            logger.debug(
                'provenance_not_found',
                project=project,
                version=version,
                filename=filename,
            )
            return None

        response.raise_for_status()
        return Provenance.model_validate_json(response.content)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            'provenance_fetch_http_error',
            project=project,
            version=version,
            status_code=exc.response.status_code,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'provenance_fetch_error',
            project=project,
            version=version,
            error=str(exc),
        )
        return None


def sign_distributions(
    dist_paths: list[Path],
    *,
    output_dir: Path | None = None,
    identity_token: str = '',
    dry_run: bool = False,
) -> list[AttestationResult]:
    """Sign multiple distributions with PEP 740 attestations.

    Args:
        dist_paths: Paths to ``.tar.gz`` and ``.whl`` files.
        output_dir: Directory for attestation files.
        identity_token: Explicit OIDC identity token.
        dry_run: If ``True``, report what would be signed.

    Returns:
        List of :class:`AttestationResult` for each distribution.
    """
    return [
        sign_distribution(
            p,
            output_dir=output_dir,
            identity_token=identity_token,
            dry_run=dry_run,
        )
        for p in dist_paths
    ]


def make_publisher(
    *,
    kind: str,
    repository: str = '',
    workflow: str = '',
    environment: str | None = None,
    email: str = '',
) -> Publisher:
    """Create a Trusted Publisher identity for verification.

    Args:
        kind: Publisher kind: ``"GitHub"``, ``"GitLab"``, or ``"Google"``.
        repository: Repository slug (e.g. ``"firebase/genkit"``).
            Required for GitHub and GitLab publishers.
        workflow: Workflow filename (GitHub) or CI config path (GitLab).
            Required for GitHub and GitLab publishers.
        environment: Optional deployment environment name.
        email: Service account email. Required for Google publishers.

    Returns:
        A :class:`Publisher` instance.

    Raises:
        ValueError: If ``kind`` is not recognized or required fields
            are missing.
    """
    kind_lower = kind.lower()
    if kind_lower == 'github':
        if not repository or not workflow:
            raise ValueError("GitHub publisher requires 'repository' and 'workflow'.")
        return GitHubPublisher(
            repository=repository,
            workflow=workflow,
            environment=environment,
        )
    if kind_lower == 'gitlab':
        if not repository or not workflow:
            raise ValueError("GitLab publisher requires 'repository' and 'workflow'.")
        return GitLabPublisher(
            repository=repository,
            workflow_filepath=workflow,
            environment=environment,
        )
    if kind_lower == 'google':
        if not email:
            raise ValueError("Google publisher requires 'email'.")
        return GooglePublisher(email=email)

    raise ValueError(f"Unknown publisher kind: {kind!r}. Expected 'GitHub', 'GitLab', or 'Google'.")


__all__ = [
    'AttestationResult',
    'convert_bundle_to_attestation',
    'fetch_provenance',
    'make_publisher',
    'sign_distribution',
    'sign_distributions',
    'verify_attestation',
]
