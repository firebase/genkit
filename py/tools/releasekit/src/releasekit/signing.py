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

r"""Package signing via Sigstore.

Provides keyless signing of release artifacts using `sigstore-python`_.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Sigstore            │ Keyless signing — uses OIDC identity (e.g.   │
    │                     │ GitHub Actions) instead of GPG keys.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Bundle              │ A ``.sigstore.json`` file containing the      │
    │                     │ signature, certificate, and transparency log  │
    │                     │ entry for an artifact.                        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Verification        │ Checks that a bundle matches the artifact     │
    │                     │ and was signed by a trusted identity.         │
    └─────────────────────┴────────────────────────────────────────────────┘

Signing flow::

    sign_artifact(artifact_path)
         │
         ├── Read artifact bytes
         ├── Obtain OIDC identity (ambient CI creds or interactive OAuth2)
         ├── sigstore.sign.SigningContext.sign(artifact_bytes)
         ├── Write .sigstore.json bundle
         └── Return SigningResult(signed=True)

Verification flow::

    verify_artifact(artifact_path, bundle_path, identity=..., issuer=...)
         │
         ├── Read artifact bytes + bundle JSON
         ├── sigstore.verify.Verifier.verify(artifact_bytes, bundle)
         └── Return VerificationResult(verified=True)

Usage::

    from releasekit.signing import sign_artifact, verify_artifact

    result = sign_artifact(Path('dist/genkit-0.5.0.tar.gz'))
    if result.signed:
        vr = verify_artifact(
            Path('dist/genkit-0.5.0.tar.gz'),
            result.bundle_path,
            identity='release@example.com',
            issuer='https://accounts.google.com',
        )

.. _sigstore-python: https://github.com/sigstore/sigstore-python
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sigstore.models import Bundle, ClientTrustConfig
from sigstore.oidc import IdentityToken, detect_credential
from sigstore.sign import SigningContext
from sigstore.verify import Verifier
from sigstore.verify.policy import Identity, UnsafeNoOp

from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SigningResult:
    """Result of a signing operation.

    Attributes:
        artifact_path: Path to the signed artifact.
        bundle_path: Path to the ``.sigstore.json`` bundle (empty if skipped).
        signed: Whether the artifact was actually signed.
        reason: Human-readable reason if signing was skipped.
    """

    artifact_path: Path
    bundle_path: Path = Path()
    signed: bool = False
    reason: str = ''


@dataclass(frozen=True)
class VerificationResult:
    """Result of a verification operation.

    Attributes:
        artifact_path: Path to the verified artifact.
        bundle_path: Path to the bundle used for verification.
        verified: Whether verification succeeded.
        reason: Human-readable reason if verification failed.
    """

    artifact_path: Path
    bundle_path: Path = Path()
    verified: bool = False
    reason: str = ''


def sign_artifact(
    artifact_path: Path,
    *,
    output_dir: Path | None = None,
    identity_token: str = '',
    dry_run: bool = False,
) -> SigningResult:
    """Sign a release artifact using Sigstore keyless signing.

    Uses ambient OIDC credentials (GitHub Actions, Google Cloud, etc.)
    when available, falling back to interactive OAuth2 browser flow.

    Args:
        artifact_path: Path to the artifact to sign.
        output_dir: Directory for the bundle file (defaults to artifact's dir).
        identity_token: Explicit OIDC identity token. If empty, sigstore
            will attempt ambient credential detection or interactive OAuth2.
        dry_run: If ``True``, report what would be signed without signing.

    Returns:
        A :class:`SigningResult` with the outcome.
    """
    if not artifact_path.exists():
        return SigningResult(
            artifact_path=artifact_path,
            reason=f'Artifact not found: {artifact_path}',
        )

    bundle_dir = output_dir or artifact_path.parent
    bundle_path = bundle_dir / f'{artifact_path.name}.sigstore.json'

    if dry_run:
        logger.info(
            'signing_dry_run',
            artifact=str(artifact_path),
            bundle=str(bundle_path),
        )
        return SigningResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            reason='dry-run: would sign',
        )

    # Real signing via sigstore.
    try:
        artifact_bytes = artifact_path.read_bytes()

        # Obtain OIDC identity token (ambient CI creds or explicit).
        if identity_token:
            token = IdentityToken(identity_token)
        else:
            raw = detect_credential()
            if raw is None:
                return SigningResult(
                    artifact_path=artifact_path,
                    bundle_path=bundle_path,
                    reason='No ambient OIDC credential detected (set --identity-token or run in CI)',
                )
            token = IdentityToken(raw)

        # Create signing context with production Sigstore infrastructure.
        trust_config = ClientTrustConfig.production()
        ctx = SigningContext.from_trust_config(trust_config)

        with ctx.signer(token) as signer:
            bundle = signer.sign_artifact(input_=artifact_bytes)

        # Write the bundle.
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_json = bundle.to_json()
        bundle_path.write_text(bundle_json, encoding='utf-8')

        logger.info(
            'artifact_signed',
            artifact=str(artifact_path),
            bundle=str(bundle_path),
        )
        return SigningResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            signed=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'signing_failed',
            artifact=str(artifact_path),
            error=str(exc),
        )
        return SigningResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            reason=f'Signing failed: {exc}',
        )


def verify_artifact(
    artifact_path: Path,
    bundle_path: Path,
    *,
    identity: str = '',
    issuer: str = '',
) -> VerificationResult:
    """Verify a Sigstore bundle against an artifact.

    Args:
        artifact_path: Path to the artifact to verify.
        bundle_path: Path to the ``.sigstore.json`` bundle.
        identity: Expected certificate identity (email or URI).
            If empty, verification checks only the signature, not the signer.
        issuer: Expected OIDC issuer URL (e.g. ``https://accounts.google.com``).

    Returns:
        A :class:`VerificationResult` with the outcome.
    """
    if not artifact_path.exists():
        return VerificationResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            reason=f'Artifact not found: {artifact_path}',
        )

    if not bundle_path.exists():
        return VerificationResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            reason=f'Bundle not found: {bundle_path}',
        )

    try:
        artifact_bytes = artifact_path.read_bytes()
        bundle_json = bundle_path.read_text(encoding='utf-8')
        bundle = Bundle.from_json(bundle_json)

        verifier = Verifier.production()

        if identity and issuer:
            policy = Identity(identity=identity, issuer=issuer)
        else:
            # No identity constraint — verify signature only.
            policy = UnsafeNoOp()

        verifier.verify_artifact(
            input_=artifact_bytes,
            bundle=bundle,
            policy=policy,
        )

        logger.info(
            'artifact_verified',
            artifact=str(artifact_path),
            bundle=str(bundle_path),
        )
        return VerificationResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            verified=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            'verification_failed',
            artifact=str(artifact_path),
            error=str(exc),
        )
        return VerificationResult(
            artifact_path=artifact_path,
            bundle_path=bundle_path,
            reason=f'Verification failed: {exc}',
        )


def sign_artifacts(
    artifact_paths: list[Path],
    *,
    output_dir: Path | None = None,
    identity_token: str = '',
    dry_run: bool = False,
) -> list[SigningResult]:
    """Sign multiple release artifacts.

    Args:
        artifact_paths: Paths to artifacts to sign.
        output_dir: Directory for bundle files (defaults to each artifact's dir).
        identity_token: Explicit OIDC identity token.
        dry_run: If ``True``, report what would be signed without signing.

    Returns:
        List of :class:`SigningResult` for each artifact.
    """
    return [
        sign_artifact(
            p,
            output_dir=output_dir,
            identity_token=identity_token,
            dry_run=dry_run,
        )
        for p in artifact_paths
    ]


__all__ = [
    'SigningResult',
    'VerificationResult',
    'sign_artifact',
    'sign_artifacts',
    'verify_artifact',
]
