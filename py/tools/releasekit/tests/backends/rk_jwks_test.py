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

"""Tests for JWT cryptographic signature verification via JWKS.

Validates the JWKS fetching, caching, and JWT signature verification
logic in :mod:`releasekit.backends.validation.jwks`.

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ What We Test                                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ RSA signing         │ Generate RSA key pair, sign JWT, verify via   │
    │                     │ JWKS endpoint.                                │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ EC signing          │ Generate EC P-256 key pair, sign JWT, verify. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Discovery fallback  │ When OIDC discovery fails, result.fallback    │
    │                     │ is True.                                      │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Expired token       │ Expired JWT returns verified=False.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Forged token        │ JWT signed with wrong key returns             │
    │                     │ verified=False.                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Cache               │ JWKS cache returns same client for same URI. │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    test → generate RSA/EC key → sign JWT → mock OIDC discovery + JWKS
         → verify_jwt_signature() → assert result
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import httpx
import httpx as _httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from releasekit.backends.validation.jwks import (
    JWTVerificationResult,
    _fetch_jwks_uri,
    _JWKSCache,
    clear_jwks_cache,
    verify_jwt_signature,
)

# --- Test key generation helpers ---


def _generate_rsa_key_pair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate an RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


def _generate_ec_key_pair() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Generate an EC P-256 key pair for testing."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def _sign_jwt(
    claims: dict,
    private_key: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey,
    algorithm: str = 'RS256',
    kid: str = 'test-key-1',
) -> str:
    """Sign a JWT with the given private key."""
    headers = {'kid': kid}
    return pyjwt.encode(claims, private_key, algorithm=algorithm, headers=headers)


def _make_claims(
    issuer: str = 'https://test.example.com',
    subject: str = 'test-subject',
    audience: str = '',
    exp_offset: int = 300,
) -> dict:
    """Create standard JWT claims."""
    now = int(time.time())
    claims: dict = {
        'iss': issuer,
        'sub': subject,
        'iat': now,
        'exp': now + exp_offset,
    }
    if audience:
        claims['aud'] = audience
    return claims


# --- Tests ---


class TestFetchJWKSUri:
    """Tests for OIDC discovery document fetching."""

    def test_successful_discovery(self) -> None:
        """Successful OIDC discovery returns jwks_uri."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'jwks_uri': 'https://test.example.com/.well-known/jwks.json',
        }
        mock_response.raise_for_status = MagicMock()

        with patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_response):
            uri = _fetch_jwks_uri('https://test.example.com')

        assert uri == 'https://test.example.com/.well-known/jwks.json'

    def test_discovery_missing_jwks_uri(self) -> None:
        """Discovery document without jwks_uri returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'issuer': 'https://test.example.com'}
        mock_response.raise_for_status = MagicMock()

        with patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_response):
            uri = _fetch_jwks_uri('https://test.example.com')

        assert uri is None

    def test_discovery_network_error(self) -> None:
        """Network error during discovery returns None."""
        with patch(
            'releasekit.backends.validation.jwks.httpx.get',
            side_effect=httpx.ConnectError('Connection refused'),
        ):
            uri = _fetch_jwks_uri('https://unreachable.example.com')

        assert uri is None

    def test_discovery_strips_trailing_slash(self) -> None:
        """Issuer URL with trailing slash is handled correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_response.raise_for_status = MagicMock()

        with patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_response) as mock_get:
            _fetch_jwks_uri('https://test.example.com/')

        # Should strip trailing slash before appending discovery path.
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert '/.well-known/openid-configuration' in call_url
        assert '//.well-known' not in call_url


class TestVerifyJWTSignature:
    """Tests for end-to-end JWT signature verification."""

    def test_discovery_failure_returns_fallback(self) -> None:
        """When OIDC discovery fails, result has fallback=True."""
        with patch(
            'releasekit.backends.validation.jwks.httpx.get',
            side_effect=httpx.ConnectError('fail'),
        ):
            result = verify_jwt_signature(
                'dummy.token.here',
                'https://unreachable.example.com',
            )

        assert not result.verified
        assert result.fallback
        assert 'Failed to fetch OIDC discovery' in result.error

    def test_jwks_key_fetch_failure_returns_fallback(self) -> None:
        """When JWKS key fetch fails, result has fallback=True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_response),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                side_effect=pyjwt.PyJWKClientError('JWKS fetch failed'),
            ),
        ):
            result = verify_jwt_signature(
                'dummy.token.here',
                'https://test.example.com',
            )

        assert not result.verified
        assert result.fallback
        assert 'Failed to fetch signing key' in result.error

    def test_expired_token_returns_not_verified(self) -> None:
        """Expired JWT returns verified=False with appropriate error."""
        private_key, _ = _generate_rsa_key_pair()
        claims = _make_claims(exp_offset=-100)  # Already expired.
        token = _sign_jwt(claims, private_key)

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = private_key.public_key()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
            )

        assert not result.verified
        assert not result.fallback
        assert 'expired' in result.error.lower()

    def test_invalid_signature_returns_not_verified(self) -> None:
        """JWT signed with wrong key returns verified=False."""
        signing_key, _ = _generate_rsa_key_pair()
        wrong_key, wrong_pub = _generate_rsa_key_pair()

        claims = _make_claims()
        token = _sign_jwt(claims, signing_key)  # Signed with one key.

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = wrong_pub  # Verify with different key.

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
            )

        assert not result.verified
        assert not result.fallback
        assert 'invalid' in result.error.lower() or 'signature' in result.error.lower()

    def test_valid_rsa_token_verified(self) -> None:
        """Valid RSA-signed JWT is verified successfully."""
        private_key, public_key = _generate_rsa_key_pair()
        claims = _make_claims()
        token = _sign_jwt(claims, private_key, algorithm='RS256')

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
            )

        assert result.verified
        assert not result.fallback
        assert result.claims['sub'] == 'test-subject'
        assert result.claims['iss'] == 'https://test.example.com'

    def test_valid_ec_token_verified(self) -> None:
        """Valid EC P-256-signed JWT is verified successfully."""
        private_key, public_key = _generate_ec_key_pair()
        claims = _make_claims()
        token = _sign_jwt(claims, private_key, algorithm='ES256')

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
            )

        assert result.verified
        assert result.claims['sub'] == 'test-subject'

    def test_issuer_mismatch_returns_not_verified(self) -> None:
        """JWT with wrong issuer returns verified=False."""
        private_key, public_key = _generate_rsa_key_pair()
        claims = _make_claims(issuer='https://wrong-issuer.example.com')
        token = _sign_jwt(claims, private_key)

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
            )

        assert not result.verified
        assert 'issuer' in result.error.lower()

    def test_decode_error_returns_not_verified(self) -> None:
        """Malformed JWT triggers DecodeError path."""
        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = MagicMock()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
            patch(
                'releasekit.backends.validation.jwks.jwt.decode',
                side_effect=pyjwt.DecodeError('Not enough segments'),
            ),
        ):
            result = verify_jwt_signature(
                'not.a.valid.jwt',
                'https://test.example.com',
            )

        assert not result.verified
        assert not result.fallback
        assert 'decode error' in result.error.lower()

    def test_invalid_token_error_returns_not_verified(self) -> None:
        """Generic InvalidTokenError triggers the catch-all path."""
        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = MagicMock()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
            patch(
                'releasekit.backends.validation.jwks.jwt.decode',
                side_effect=pyjwt.InvalidTokenError('Token is invalid'),
            ),
        ):
            result = verify_jwt_signature(
                'some.token.here',
                'https://test.example.com',
            )

        assert not result.verified
        assert not result.fallback
        assert 'validation error' in result.error.lower()

    def test_audience_validation_passes(self) -> None:
        """Token with matching audience is verified."""
        private_key, public_key = _generate_rsa_key_pair()
        claims = _make_claims(audience='https://my-api.example.com')
        token = _sign_jwt(claims, private_key)

        mock_discovery = MagicMock()
        mock_discovery.status_code = 200
        mock_discovery.json.return_value = {
            'jwks_uri': 'https://test.example.com/jwks',
        }
        mock_discovery.raise_for_status = MagicMock()

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch('releasekit.backends.validation.jwks.httpx.get', return_value=mock_discovery),
            patch(
                'releasekit.backends.validation.jwks._jwks_cache.get_client',
                return_value=mock_jwks_client,
            ),
        ):
            result = verify_jwt_signature(
                token,
                'https://test.example.com',
                audience='https://my-api.example.com',
            )

        assert result.verified
        assert result.claims['aud'] == 'https://my-api.example.com'

    def test_result_carries_issuer(self) -> None:
        """All results carry the issuer field."""
        with patch(
            'releasekit.backends.validation.jwks.httpx.get',
            side_effect=_httpx.ConnectError('fail'),
        ):
            result = verify_jwt_signature(
                'dummy',
                'https://my-issuer.example.com',
            )

        assert result.issuer == 'https://my-issuer.example.com'


class TestJWKSCache:
    """Tests for the JWKS client cache."""

    def test_cache_returns_same_client(self) -> None:
        """Same URI returns the same cached client."""
        cache = _JWKSCache(ttl=60)
        client1 = cache.get_client('https://example.com/jwks')
        client2 = cache.get_client('https://example.com/jwks')
        assert client1 is client2

    def test_cache_different_uris(self) -> None:
        """Different URIs return different clients."""
        cache = _JWKSCache(ttl=60)
        client1 = cache.get_client('https://a.example.com/jwks')
        client2 = cache.get_client('https://b.example.com/jwks')
        assert client1 is not client2

    def test_cache_clear(self) -> None:
        """Clearing cache causes fresh client creation."""
        cache = _JWKSCache(ttl=60)
        client1 = cache.get_client('https://example.com/jwks')
        cache.clear()
        client2 = cache.get_client('https://example.com/jwks')
        assert client1 is not client2

    def test_module_level_clear(self) -> None:
        """Module-level clear_jwks_cache() works."""
        clear_jwks_cache()  # Should not raise.

    def test_cache_ttl_within_returns_same(self) -> None:
        """Cache entry within TTL returns the same client."""
        cache = _JWKSCache(ttl=10)
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=100.0):
            client1 = cache.get_client('https://example.com/jwks')

        # Within TTL: same client.
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=105.0):
            client2 = cache.get_client('https://example.com/jwks')
        assert client1 is client2

    def test_cache_ttl_expired_returns_new(self) -> None:
        """Cache entry after TTL returns a new client."""
        cache = _JWKSCache(ttl=10)
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=100.0):
            client1 = cache.get_client('https://example.com/jwks')

        # After TTL: new client.
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=111.0):
            client2 = cache.get_client('https://example.com/jwks')
        assert client2 is not client1

    def test_cache_ttl_boundary_returns_same(self) -> None:
        """Cache entry exactly at TTL boundary still returns same client."""
        cache = _JWKSCache(ttl=10)
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=100.0):
            client1 = cache.get_client('https://example.com/jwks')

        # Exactly at boundary (100 + 10 = 110, 109.9 < 10 diff): same client.
        with patch('releasekit.backends.validation.jwks.time.monotonic', return_value=109.9):
            client2 = cache.get_client('https://example.com/jwks')
        assert client1 is client2


class TestJWTVerificationResult:
    """Tests for the JWTVerificationResult dataclass."""

    def test_default_values(self) -> None:
        """Default result is not verified, no fallback."""
        result = JWTVerificationResult()
        assert not result.verified
        assert not result.fallback
        assert result.claims == {}
        assert result.issuer == ''
        assert result.error == ''

    def test_verified_result(self) -> None:
        """Verified result carries claims."""
        result = JWTVerificationResult(
            verified=True,
            claims={'sub': 'test'},
            issuer='https://example.com',
        )
        assert result.verified
        assert result.claims['sub'] == 'test'

    def test_fallback_result(self) -> None:
        """Fallback result has correct fields."""
        result = JWTVerificationResult(
            fallback=True,
            error='Network error',
            issuer='https://example.com',
        )
        assert not result.verified
        assert result.fallback
        assert result.error == 'Network error'

    def test_error_result(self) -> None:
        """Error result with no fallback."""
        result = JWTVerificationResult(
            error='Signature invalid',
            issuer='https://example.com',
        )
        assert not result.verified
        assert not result.fallback
        assert 'Signature invalid' in result.error
