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

"""Tests for PEP 740 digital attestations.

Key Concepts:
    - PEP 740 attestations bind distribution files to Sigstore identities.
    - ``pypi-attestations`` provides ``Attestation.sign()`` and ``.verify()``.
    - ``Distribution.from_file()`` computes SHA-256 digest of a dist file.
    - ``Provenance`` wraps attestation bundles with publisher identity.
    - The PyPI Integrity API serves provenance at
      ``/integrity/<proj>/<ver>/<file>/provenance``.

Data Flow::

    test → create temp dist files → mock Sigstore/pypi-attestations
         → call sign/verify/convert/fetch → assert AttestationResult
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pypi_attestations import (
    Attestation,
    AttestationError,
    ConversionError,
    Distribution,
    GitHubPublisher,
    GitLabPublisher,
    GooglePublisher,
    Provenance,
    VerificationError,
)
from releasekit.attestations import (
    AttestationResult,
    convert_bundle_to_attestation,
    fetch_provenance,
    make_publisher,
    sign_distribution,
    sign_distributions,
    verify_attestation,
)


@pytest.fixture()
def dist_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a fake distribution file."""
    dist = tmp_path / 'dist'
    dist.mkdir()
    return dist


@pytest.fixture()
def fake_wheel(dist_dir: Path) -> Path:
    """Create a fake wheel file."""
    whl = dist_dir / 'mypackage-1.0.0-py3-none-any.whl'
    whl.write_bytes(b'fake wheel content for testing')
    return whl


@pytest.fixture()
def fake_sdist(dist_dir: Path) -> Path:
    """Create a fake sdist file."""
    sdist = dist_dir / 'mypackage-1.0.0.tar.gz'
    sdist.write_bytes(b'fake sdist content for testing')
    return sdist


# sign_distribution


class TestSignDistribution:
    """Tests for PEP 740 attestation signing."""

    def test_missing_dist_returns_reason(self, tmp_path: Path) -> None:
        """Missing distribution file returns a reason, not an error."""
        result = sign_distribution(tmp_path / 'nonexistent.whl')
        assert not result.signed
        assert 'not found' in result.reason.lower()

    def test_dry_run_does_not_sign(self, fake_wheel: Path) -> None:
        """Dry run reports what would be signed without signing."""
        result = sign_distribution(fake_wheel, dry_run=True)
        assert not result.signed
        assert 'dry-run' in result.reason
        assert result.dist_path == fake_wheel
        assert result.attestation_path.name.endswith('.publish.attestation')

    def test_no_oidc_credential_returns_reason(self, fake_wheel: Path) -> None:
        """No ambient OIDC credential returns a reason."""
        with patch(
            'releasekit.attestations.detect_credential',
            return_value=None,
        ):
            result = sign_distribution(fake_wheel)
        assert not result.signed
        assert 'oidc' in result.reason.lower()

    def test_explicit_identity_token(self, fake_wheel: Path) -> None:
        """Explicit identity token is used for signing."""
        mock_signer = MagicMock()
        mock_attestation = MagicMock(spec=Attestation)
        mock_attestation.model_dump_json.return_value = '{"version": 1}'

        mock_ctx = MagicMock()
        mock_ctx.signer.return_value.__enter__ = MagicMock(return_value=mock_signer)
        mock_ctx.signer.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch('releasekit.attestations.SigningContext.from_trust_config', return_value=mock_ctx),
            patch('releasekit.attestations.ClientTrustConfig.production'),
            patch('releasekit.attestations.Attestation.sign', return_value=mock_attestation),
            patch('releasekit.attestations.IdentityToken'),
        ):
            result = sign_distribution(fake_wheel, identity_token='test-token')

        assert result.signed
        assert result.predicate_type == 'https://docs.pypi.org/attestations/publish/v1'

    def test_attestation_error_returns_reason(self, fake_wheel: Path) -> None:
        """AttestationError during signing returns a reason."""
        with (
            patch(
                'releasekit.attestations.detect_credential',
                return_value='fake-token',
            ),
            patch('releasekit.attestations.IdentityToken'),
            patch('releasekit.attestations.ClientTrustConfig.production'),
            patch(
                'releasekit.attestations.SigningContext.from_trust_config',
                side_effect=AttestationError('signing failed'),
            ),
        ):
            result = sign_distribution(fake_wheel)
        assert not result.signed
        assert 'signing failed' in result.reason

    def test_unexpected_error_returns_reason(self, fake_wheel: Path) -> None:
        """Unexpected error during signing returns a reason."""
        with (
            patch(
                'releasekit.attestations.detect_credential',
                return_value='fake-token',
            ),
            patch('releasekit.attestations.IdentityToken'),
            patch('releasekit.attestations.ClientTrustConfig.production'),
            patch(
                'releasekit.attestations.SigningContext.from_trust_config',
                side_effect=RuntimeError('unexpected'),
            ),
        ):
            result = sign_distribution(fake_wheel)
        assert not result.signed
        assert 'unexpected' in result.reason.lower()

    def test_custom_output_dir(self, fake_wheel: Path, tmp_path: Path) -> None:
        """Custom output directory is used for attestation file."""
        out = tmp_path / 'attestations'
        result = sign_distribution(fake_wheel, output_dir=out, dry_run=True)
        assert result.attestation_path.parent == out

    def test_conversion_error_returns_reason(self, fake_wheel: Path) -> None:
        """ConversionError during signing returns a reason."""
        with (
            patch(
                'releasekit.attestations.detect_credential',
                return_value='fake-token',
            ),
            patch('releasekit.attestations.IdentityToken'),
            patch('releasekit.attestations.ClientTrustConfig.production'),
            patch(
                'releasekit.attestations.SigningContext.from_trust_config',
                side_effect=ConversionError('conversion failed'),
            ),
        ):
            result = sign_distribution(fake_wheel)
        assert not result.signed
        assert 'conversion failed' in result.reason


# verify_attestation


class TestVerifyAttestation:
    """Tests for PEP 740 attestation verification."""

    def test_missing_dist_returns_reason(self, tmp_path: Path) -> None:
        """Missing distribution returns a reason."""
        attest = tmp_path / 'fake.publish.attestation'
        attest.write_text('{}')
        result = verify_attestation(tmp_path / 'nonexistent.whl', attest)
        assert not result.verified
        assert 'not found' in result.reason.lower()

    def test_missing_attestation_returns_reason(self, fake_wheel: Path, tmp_path: Path) -> None:
        """Missing attestation file returns a reason."""
        result = verify_attestation(fake_wheel, tmp_path / 'nonexistent.attestation')
        assert not result.verified
        assert 'not found' in result.reason.lower()

    def test_verification_error_returns_reason(self, fake_wheel: Path, dist_dir: Path) -> None:
        """VerificationError returns a reason."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        mock_attestation = MagicMock()
        mock_attestation.verify.side_effect = VerificationError('bad signature')

        with (
            patch.object(Distribution, 'from_file', return_value=MagicMock()),
            patch.object(
                Attestation,
                'model_validate_json',
                return_value=mock_attestation,
            ),
        ):
            publisher = GitHubPublisher(
                repository='firebase/genkit',
                workflow='release.yml',
            )
            result = verify_attestation(fake_wheel, attest, publisher=publisher)
        assert not result.verified
        assert 'bad signature' in result.reason

    def test_unexpected_error_returns_reason(self, fake_wheel: Path, dist_dir: Path) -> None:
        """Unexpected error during verification returns a reason."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        with (
            patch.object(Distribution, 'from_file', side_effect=RuntimeError('boom')),
        ):
            result = verify_attestation(fake_wheel, attest)
        assert not result.verified
        assert 'boom' in result.reason

    def test_verify_without_publisher(self, fake_wheel: Path, dist_dir: Path) -> None:
        """Verification without publisher uses UnsafeNoOp policy."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        mock_attestation = MagicMock()
        mock_attestation.statement = {'predicateType': 'https://docs.pypi.org/attestations/publish/v1'}
        mock_attestation.to_bundle.return_value = MagicMock()

        mock_verifier = MagicMock()
        mock_verifier.verify_dsse.return_value = ('application/vnd.in-toto+json', b'{}')

        with (
            patch.object(Distribution, 'from_file', return_value=MagicMock()),
            patch.object(Attestation, 'model_validate_json', return_value=mock_attestation),
            patch('sigstore.verify.Verifier.production', return_value=mock_verifier),
        ):
            result = verify_attestation(fake_wheel, attest, publisher=None)

        assert result.verified
        assert result.predicate_type == 'https://docs.pypi.org/attestations/publish/v1'

    def test_verify_with_github_publisher(self, fake_wheel: Path, dist_dir: Path) -> None:
        """Verification with GitHub publisher calls attestation.verify()."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        mock_attestation = MagicMock(spec=Attestation)
        mock_attestation.verify.return_value = (
            'https://docs.pypi.org/attestations/publish/v1',
            None,
        )

        with (
            patch.object(Distribution, 'from_file', return_value=MagicMock()),
            patch.object(Attestation, 'model_validate_json', return_value=mock_attestation),
        ):
            publisher = GitHubPublisher(
                repository='firebase/genkit',
                workflow='release.yml',
            )
            result = verify_attestation(fake_wheel, attest, publisher=publisher)

        assert result.verified
        mock_attestation.verify.assert_called_once()

    def test_verify_with_staging(self, fake_wheel: Path, dist_dir: Path) -> None:
        """Staging flag is passed through to verification."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        mock_attestation = MagicMock()
        mock_attestation.statement = {'predicateType': 'test'}
        mock_attestation.to_bundle.return_value = MagicMock()

        mock_verifier = MagicMock()
        mock_verifier.verify_dsse.return_value = ('application/vnd.in-toto+json', b'{}')

        with (
            patch.object(Distribution, 'from_file', return_value=MagicMock()),
            patch.object(Attestation, 'model_validate_json', return_value=mock_attestation),
            patch('sigstore.verify.Verifier.staging', return_value=mock_verifier) as mock_staging,
        ):
            result = verify_attestation(
                fake_wheel,
                attest,
                publisher=None,
                staging=True,
            )

        assert result.verified
        mock_staging.assert_called_once_with(offline=False)

    def test_conversion_error_returns_reason(self, fake_wheel: Path, dist_dir: Path) -> None:
        """ConversionError during verification returns a reason."""
        attest = dist_dir / 'fake.publish.attestation'
        attest.write_text('{"version": 1}')

        with (
            patch.object(Distribution, 'from_file', return_value=MagicMock()),
            patch.object(
                Attestation,
                'model_validate_json',
                side_effect=ConversionError('bad conversion'),
            ),
        ):
            result = verify_attestation(fake_wheel, attest)
        assert not result.verified
        assert 'bad conversion' in result.reason


# convert_bundle_to_attestation


class TestConvertBundleToAttestation:
    """Tests for Sigstore bundle → PEP 740 attestation conversion."""

    def test_missing_bundle_returns_reason(self, tmp_path: Path) -> None:
        """Missing bundle file returns a reason."""
        result = convert_bundle_to_attestation(tmp_path / 'nonexistent.sigstore.json')
        assert not result.signed
        assert 'not found' in result.reason.lower()

    def test_successful_conversion(self, tmp_path: Path) -> None:
        """Successful conversion writes attestation file."""
        bundle_path = tmp_path / 'pkg-1.0.tar.gz.sigstore.json'
        bundle_path.write_text('{"fake": "bundle"}')

        mock_bundle = MagicMock()
        mock_attestation = MagicMock(spec=Attestation)
        mock_attestation.model_dump_json.return_value = '{"version": 1}'

        with (
            patch('releasekit.attestations.Bundle.from_json', return_value=mock_bundle),
            patch.object(Attestation, 'from_bundle', return_value=mock_attestation),
        ):
            result = convert_bundle_to_attestation(bundle_path)

        assert result.signed
        expected_path = tmp_path / 'pkg-1.0.tar.gz.publish.attestation'
        assert result.attestation_path == expected_path
        assert expected_path.exists()

    def test_custom_output_path(self, tmp_path: Path) -> None:
        """Custom output path is used."""
        bundle_path = tmp_path / 'pkg.sigstore.json'
        bundle_path.write_text('{}')
        out = tmp_path / 'custom.attestation'

        mock_bundle = MagicMock()
        mock_attestation = MagicMock(spec=Attestation)
        mock_attestation.model_dump_json.return_value = '{}'

        with (
            patch('releasekit.attestations.Bundle.from_json', return_value=mock_bundle),
            patch.object(Attestation, 'from_bundle', return_value=mock_attestation),
        ):
            result = convert_bundle_to_attestation(bundle_path, output_path=out)

        assert result.attestation_path == out

    def test_conversion_error_returns_reason(self, tmp_path: Path) -> None:
        """ConversionError returns a reason."""
        bundle_path = tmp_path / 'bad.sigstore.json'
        bundle_path.write_text('{}')

        with patch(
            'releasekit.attestations.Bundle.from_json',
            side_effect=ConversionError('invalid bundle'),
        ):
            result = convert_bundle_to_attestation(bundle_path)
        assert not result.signed
        assert 'invalid bundle' in result.reason

    def test_unexpected_error_returns_reason(self, tmp_path: Path) -> None:
        """Unexpected error returns a reason."""
        bundle_path = tmp_path / 'bad.sigstore.json'
        bundle_path.write_text('{}')

        with patch(
            'releasekit.attestations.Bundle.from_json',
            side_effect=RuntimeError('boom'),
        ):
            result = convert_bundle_to_attestation(bundle_path)
        assert not result.signed
        assert 'boom' in result.reason

    def test_non_sigstore_extension(self, tmp_path: Path) -> None:
        """Bundle without .sigstore.json extension still works."""
        bundle_path = tmp_path / 'pkg-1.0.tar.gz.bundle'
        bundle_path.write_text('{}')

        mock_bundle = MagicMock()
        mock_attestation = MagicMock(spec=Attestation)
        mock_attestation.model_dump_json.return_value = '{}'

        with (
            patch('releasekit.attestations.Bundle.from_json', return_value=mock_bundle),
            patch.object(Attestation, 'from_bundle', return_value=mock_attestation),
        ):
            result = convert_bundle_to_attestation(bundle_path)

        # Should use full filename as stem since it doesn't end with .sigstore.json.
        assert result.attestation_path.name == 'pkg-1.0.tar.gz.bundle.publish.attestation'


# fetch_provenance


@pytest.mark.asyncio()
class TestFetchProvenance:
    """Tests for fetching PEP 740 provenance from PyPI."""

    async def test_successful_fetch(self) -> None:
        """Successful fetch returns Provenance object."""
        provenance_data = {
            'version': 1,
            'attestation_bundles': [
                {
                    'publisher': {
                        'kind': 'GitHub',
                        'repository': 'pypa/sampleproject',
                        'workflow': 'release.yml',
                    },
                    'attestations': [],
                },
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(provenance_data).encode()
        mock_response.raise_for_status = MagicMock()

        with patch('releasekit.attestations.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await fetch_provenance(
                'sampleproject',
                '4.0.0',
                'sampleproject-4.0.0.tar.gz',
            )

        assert result is not None
        assert isinstance(result, Provenance)

    async def test_404_returns_none(self) -> None:
        """404 response returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('releasekit.attestations.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await fetch_provenance(
                'nonexistent',
                '1.0.0',
                'nonexistent-1.0.0.tar.gz',
            )

        assert result is None

    async def test_http_error_returns_none(self) -> None:
        """HTTP error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            'Server Error',
            request=MagicMock(),
            response=mock_response,
        )

        with patch('releasekit.attestations.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await fetch_provenance(
                'pkg',
                '1.0.0',
                'pkg-1.0.0.tar.gz',
            )

        assert result is None

    async def test_network_error_returns_none(self) -> None:
        """Network error returns None."""
        with patch('releasekit.attestations.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError('connection refused'))
            mock_client_cls.return_value = mock_client

            result = await fetch_provenance(
                'pkg',
                '1.0.0',
                'pkg-1.0.0.tar.gz',
            )

        assert result is None

    async def test_custom_pypi_url(self) -> None:
        """Custom PyPI URL is used."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('releasekit.attestations.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await fetch_provenance(
                'pkg',
                '1.0.0',
                'pkg-1.0.0.tar.gz',
                pypi_url='https://test.pypi.org',
            )

        call_args = mock_client.get.call_args
        assert 'test.pypi.org' in call_args[0][0]


# sign_distributions


class TestSignDistributions:
    """Tests for batch signing."""

    def test_empty_list(self) -> None:
        """Empty list returns empty results."""
        assert sign_distributions([]) == []

    def test_multiple_dists(self, fake_wheel: Path, fake_sdist: Path) -> None:
        """Multiple distributions are all signed (dry run)."""
        results = sign_distributions(
            [fake_wheel, fake_sdist],
            dry_run=True,
        )
        assert len(results) == 2
        assert all('dry-run' in r.reason for r in results)

    def test_mixed_existing_and_missing(self, fake_wheel: Path, tmp_path: Path) -> None:
        """Mix of existing and missing files."""
        missing = tmp_path / 'nonexistent.whl'
        results = sign_distributions([fake_wheel, missing], dry_run=True)
        assert len(results) == 2
        assert 'dry-run' in results[0].reason
        assert 'not found' in results[1].reason.lower()


# make_publisher


class TestMakePublisher:
    """Tests for Trusted Publisher factory."""

    def test_github_publisher(self) -> None:
        """GitHub publisher is created correctly."""
        pub = make_publisher(
            kind='GitHub',
            repository='firebase/genkit',
            workflow='release.yml',
        )
        assert isinstance(pub, GitHubPublisher)
        assert pub.repository == 'firebase/genkit'
        assert pub.workflow == 'release.yml'

    def test_github_publisher_with_environment(self) -> None:
        """GitHub publisher with environment."""
        pub = make_publisher(
            kind='GitHub',
            repository='firebase/genkit',
            workflow='release.yml',
            environment='production',
        )
        assert isinstance(pub, GitHubPublisher)
        assert pub.environment == 'production'

    def test_github_missing_repository(self) -> None:
        """GitHub publisher without repository raises."""
        with pytest.raises(ValueError, match='repository'):
            make_publisher(kind='GitHub', workflow='release.yml')

    def test_github_missing_workflow(self) -> None:
        """GitHub publisher without workflow raises."""
        with pytest.raises(ValueError, match='workflow'):
            make_publisher(kind='GitHub', repository='firebase/genkit')

    def test_gitlab_publisher(self) -> None:
        """GitLab publisher is created correctly."""
        pub = make_publisher(
            kind='GitLab',
            repository='group/project',
            workflow='.gitlab-ci.yml',
        )
        assert isinstance(pub, GitLabPublisher)
        assert pub.repository == 'group/project'
        assert pub.workflow_filepath == '.gitlab-ci.yml'

    def test_gitlab_missing_fields(self) -> None:
        """GitLab publisher without required fields raises."""
        with pytest.raises(ValueError, match='repository'):
            make_publisher(kind='GitLab', workflow='.gitlab-ci.yml')

    def test_google_publisher(self) -> None:
        """Google publisher is created correctly."""
        pub = make_publisher(
            kind='Google',
            email='release@project.iam.gserviceaccount.com',
        )
        assert isinstance(pub, GooglePublisher)
        assert pub.email == 'release@project.iam.gserviceaccount.com'

    def test_google_missing_email(self) -> None:
        """Google publisher without email raises."""
        with pytest.raises(ValueError, match='email'):
            make_publisher(kind='Google')

    def test_unknown_kind(self) -> None:
        """Unknown publisher kind raises."""
        with pytest.raises(ValueError, match='Unknown publisher kind'):
            make_publisher(kind='Azure')

    def test_case_insensitive_kind(self) -> None:
        """Publisher kind is case-insensitive."""
        pub = make_publisher(
            kind='github',
            repository='firebase/genkit',
            workflow='release.yml',
        )
        assert isinstance(pub, GitHubPublisher)

    def test_gitlab_case_insensitive(self) -> None:
        """GitLab kind is case-insensitive."""
        pub = make_publisher(
            kind='GITLAB',
            repository='group/project',
            workflow='.gitlab-ci.yml',
        )
        assert isinstance(pub, GitLabPublisher)

    def test_google_case_insensitive(self) -> None:
        """Google kind is case-insensitive."""
        pub = make_publisher(
            kind='GOOGLE',
            email='sa@project.iam.gserviceaccount.com',
        )
        assert isinstance(pub, GooglePublisher)


# AttestationResult


class TestAttestationResult:
    """Tests for the AttestationResult dataclass."""

    def test_default_values(self) -> None:
        """Default result is not signed, not verified."""
        result = AttestationResult()
        assert not result.signed
        assert not result.verified
        assert result.predicate_type == ''
        assert result.reason == ''

    def test_signed_result(self) -> None:
        """Signed result has correct fields."""
        result = AttestationResult(
            dist_path=Path('dist/pkg-1.0.whl'),
            attestation_path=Path('dist/pkg-1.0.whl.publish.attestation'),
            signed=True,
            predicate_type='https://docs.pypi.org/attestations/publish/v1',
        )
        assert result.signed
        assert not result.verified
        assert 'publish/v1' in result.predicate_type

    def test_verified_result(self) -> None:
        """Verified result has correct fields."""
        result = AttestationResult(
            dist_path=Path('dist/pkg-1.0.whl'),
            verified=True,
        )
        assert result.verified
        assert not result.signed

    def test_frozen(self) -> None:
        """AttestationResult is frozen."""
        result = AttestationResult()
        with pytest.raises(AttributeError):
            result.signed = True  # type: ignore[misc]
