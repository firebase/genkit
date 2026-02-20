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

"""Tests for releasekit.signing — Sigstore keyless signing.

Covers:
- SigningResult and VerificationResult dataclasses
- sign_artifact() signing flow
- verify_artifact() verification flow
- Dry-run mode
- Missing artifact / bundle handling
"""

from __future__ import annotations

import unittest.mock
from pathlib import Path

from releasekit.signing import (
    SigningResult,
    VerificationResult,
    sign_artifact,
    sign_artifacts,
    verify_artifact,
)


class TestSigningResult:
    """Tests for SigningResult dataclass."""

    def test_defaults(self) -> None:
        """Default fields are empty/False."""
        r = SigningResult(artifact_path=Path('foo.tar.gz'))
        assert r.signed is False
        assert r.bundle_path == Path()
        assert r.reason == ''

    def test_frozen(self) -> None:
        """Result is immutable."""
        r = SigningResult(artifact_path=Path('foo.tar.gz'))
        try:
            r.signed = True  # type: ignore[misc]
            raise AssertionError('Should be frozen')
        except AttributeError:
            pass


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_defaults(self) -> None:
        """Default fields are empty/False."""
        r = VerificationResult(artifact_path=Path('foo.tar.gz'))
        assert r.verified is False
        assert r.bundle_path == Path()
        assert r.reason == ''

    def test_frozen(self) -> None:
        """Result is immutable."""
        r = VerificationResult(artifact_path=Path('foo.tar.gz'))
        try:
            r.verified = True  # type: ignore[misc]
            raise AssertionError('Should be frozen')
        except AttributeError:
            pass


class TestSignArtifact:
    """Tests for sign_artifact()."""

    def test_missing_artifact(self, tmp_path: Path) -> None:
        """Missing artifact returns reason."""
        result = sign_artifact(tmp_path / 'nonexistent.tar.gz')
        assert result.signed is False
        assert 'not found' in result.reason

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports what would be signed."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')

        result = sign_artifact(artifact, dry_run=True)

        assert result.signed is False
        assert 'dry-run' in result.reason
        assert result.bundle_path.name == 'pkg-1.0.0.tar.gz.sigstore.json'

    def test_custom_output_dir(self, tmp_path: Path) -> None:
        """Custom output_dir is used for bundle path."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')
        out = tmp_path / 'bundles'

        result = sign_artifact(artifact, output_dir=out)
        assert result.bundle_path == out / 'pkg-1.0.0.tar.gz.sigstore.json'

    def test_signing_error_caught(self, tmp_path: Path) -> None:
        """When signing fails, error is caught."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')

        mock_ctx = unittest.mock.MagicMock()
        mock_ctx.signer.return_value.__enter__ = unittest.mock.MagicMock(
            side_effect=RuntimeError('OIDC token unavailable'),
        )
        mock_ctx.signer.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

        with (
            unittest.mock.patch('releasekit.signing.detect_credential', return_value='fake-token'),
            unittest.mock.patch('releasekit.signing.IdentityToken'),
            unittest.mock.patch('releasekit.signing.ClientTrustConfig'),
            unittest.mock.patch('releasekit.signing.SigningContext') as mock_sc,
        ):
            mock_sc.from_trust_config.return_value = mock_ctx
            result = sign_artifact(artifact)

        assert result.signed is False
        assert 'Signing failed' in result.reason

    def test_no_ambient_credential(self, tmp_path: Path) -> None:
        """No ambient credential returns a reason."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')

        with unittest.mock.patch('releasekit.signing.detect_credential', return_value=None):
            result = sign_artifact(artifact)

        assert result.signed is False
        assert 'No ambient OIDC credential' in result.reason

    def test_signing_success_mocked(self, tmp_path: Path) -> None:
        """Successful signing writes bundle and returns signed=True."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')

        mock_bundle = unittest.mock.MagicMock()
        mock_bundle.to_json.return_value = '{"mock": true}'

        mock_signer = unittest.mock.MagicMock()
        mock_signer.sign_artifact.return_value = mock_bundle

        mock_ctx = unittest.mock.MagicMock()
        mock_ctx.signer.return_value.__enter__ = unittest.mock.MagicMock(return_value=mock_signer)
        mock_ctx.signer.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

        with (
            unittest.mock.patch('releasekit.signing.detect_credential', return_value='fake-token'),
            unittest.mock.patch('releasekit.signing.IdentityToken'),
            unittest.mock.patch('releasekit.signing.ClientTrustConfig'),
            unittest.mock.patch('releasekit.signing.SigningContext') as mock_sc,
        ):
            mock_sc.from_trust_config.return_value = mock_ctx
            result = sign_artifact(artifact)

        assert result.signed is True
        assert result.reason == ''
        bundle_path = tmp_path / 'pkg-1.0.0.tar.gz.sigstore.json'
        assert bundle_path.exists()
        assert bundle_path.read_text() == '{"mock": true}'


class TestVerifyArtifact:
    """Tests for verify_artifact()."""

    def test_missing_artifact(self, tmp_path: Path) -> None:
        """Missing artifact returns reason."""
        bundle = tmp_path / 'pkg.sigstore.json'
        bundle.write_text('{}')
        result = verify_artifact(
            tmp_path / 'nonexistent.tar.gz',
            bundle,
        )
        assert result.verified is False
        assert 'Artifact not found' in result.reason

    def test_missing_bundle(self, tmp_path: Path) -> None:
        """Missing bundle returns reason."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')
        result = verify_artifact(
            artifact,
            tmp_path / 'nonexistent.sigstore.json',
        )
        assert result.verified is False
        assert 'Bundle not found' in result.reason

    def test_verification_error_caught(self, tmp_path: Path) -> None:
        """When verification fails, error is caught."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')
        bundle = tmp_path / 'pkg-1.0.0.tar.gz.sigstore.json'
        bundle.write_text('{"invalid": true}')

        with unittest.mock.patch('releasekit.signing.Bundle') as mock_bundle_cls:
            mock_bundle_cls.from_json.side_effect = ValueError('bad bundle')
            result = verify_artifact(artifact, bundle)

        assert result.verified is False
        assert 'Verification failed' in result.reason

    def test_verification_success_mocked(self, tmp_path: Path) -> None:
        """Successful verification returns verified=True."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')
        bundle = tmp_path / 'pkg-1.0.0.tar.gz.sigstore.json'
        bundle.write_text('{"mock": true}')

        mock_verifier = unittest.mock.MagicMock()
        mock_verifier.verify_artifact.return_value = None  # no exception = success

        with (
            unittest.mock.patch('releasekit.signing.Bundle') as mock_bundle_cls,
            unittest.mock.patch('releasekit.signing.Verifier') as mock_verifier_cls,
        ):
            mock_bundle_cls.from_json.return_value = unittest.mock.MagicMock()
            mock_verifier_cls.production.return_value = mock_verifier
            result = verify_artifact(artifact, bundle)

        assert result.verified is True
        assert result.reason == ''

    def test_verification_with_identity(self, tmp_path: Path) -> None:
        """Verification with identity and issuer passes policy to verifier."""
        artifact = tmp_path / 'pkg-1.0.0.tar.gz'
        artifact.write_bytes(b'fake tarball')
        bundle = tmp_path / 'pkg-1.0.0.tar.gz.sigstore.json'
        bundle.write_text('{"mock": true}')

        mock_verifier = unittest.mock.MagicMock()
        mock_verifier.verify_artifact.return_value = None

        with (
            unittest.mock.patch('releasekit.signing.Bundle') as mock_bundle_cls,
            unittest.mock.patch('releasekit.signing.Verifier') as mock_verifier_cls,
            unittest.mock.patch('releasekit.signing.Identity') as mock_identity_cls,
        ):
            mock_bundle_cls.from_json.return_value = unittest.mock.MagicMock()
            mock_verifier_cls.production.return_value = mock_verifier
            result = verify_artifact(
                artifact,
                bundle,
                identity='release@example.com',
                issuer='https://accounts.google.com',
            )

        assert result.verified is True
        mock_identity_cls.assert_called_once_with(
            identity='release@example.com',
            issuer='https://accounts.google.com',
        )


class TestSignArtifacts:
    """Tests for sign_artifacts() batch helper."""

    def test_batch_signing(self, tmp_path: Path) -> None:
        """Signs multiple artifacts and returns list of results."""
        a1 = tmp_path / 'pkg-1.0.0.tar.gz'
        a2 = tmp_path / 'pkg-1.0.0.whl'
        a1.write_bytes(b'tarball')
        a2.write_bytes(b'wheel')

        results = sign_artifacts([a1, a2])
        assert len(results) == 2
        assert all(isinstance(r, SigningResult) for r in results)

    def test_empty_list(self, tmp_path: Path) -> None:
        """Empty list returns empty results."""
        results = sign_artifacts([])
        assert results == []
