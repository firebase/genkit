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

r"""JWKS fetching and JWT cryptographic signature verification.

Upgrades the structural-only OIDC token checks in
:mod:`~releasekit.backends.validation.oidc` with real cryptographic
verification using the issuer's JSON Web Key Set (JWKS).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ JWKS                │ A set of public keys published by the OIDC    │
    │                     │ issuer.  Used to verify JWT signatures.       │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ OIDC Discovery      │ A well-known URL that tells us where to find │
    │                     │ the JWKS for a given issuer.                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ RS256 / ES256       │ Signature algorithms used by CI platforms.    │
    │                     │ RS256 = RSA + SHA-256, ES256 = ECDSA P-256.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Fallback            │ If JWKS fetch fails (network), we fall back   │
    │                     │ to structural-only checks with a warning.     │
    └─────────────────────┴────────────────────────────────────────────────┘

Verification flow::

    verify_jwt_signature(token, issuer)
         │
         ├── Fetch OIDC discovery: {issuer}/.well-known/openid-configuration
         ├── Extract jwks_uri from discovery document
         ├── Fetch JWKS from jwks_uri (cached for jwks_cache_ttl seconds)
         ├── jwt.decode(token, key=jwks_client, algorithms=["RS256", "ES256"])
         └── Return JWTVerificationResult(verified=True, claims=...)

Usage::

    from releasekit.backends.validation.jwks import verify_jwt_signature

    result = verify_jwt_signature(token, issuer='https://token.actions.githubusercontent.com')
    if result.verified:
        print(f'Token claims: {result.claims}')
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from releasekit.logging import get_logger

logger = get_logger(__name__)

# Supported JWT signing algorithms across CI platforms.
_SUPPORTED_ALGORITHMS: list[str] = ['RS256', 'ES256']

# Default JWKS cache TTL in seconds (10 minutes).
_DEFAULT_JWKS_CACHE_TTL: int = 600

# HTTP timeout for JWKS/discovery fetches in seconds.
_FETCH_TIMEOUT: float = 10.0


@dataclass(frozen=True)
class JWTVerificationResult:
    """Result of a JWT cryptographic signature verification.

    Attributes:
        verified: Whether the signature was cryptographically verified.
        claims: Decoded JWT claims (empty dict if verification failed).
        issuer: The OIDC issuer URL.
        error: Human-readable error message if verification failed.
        fallback: Whether we fell back to structural-only validation.
    """

    verified: bool = False
    claims: dict[str, Any] = field(default_factory=dict)
    issuer: str = ''
    error: str = ''
    fallback: bool = False


class _JWKSCache:
    """Thread-safe cache for JWKS clients keyed by issuer.

    Each issuer gets its own :class:`PyJWKClient` instance. The cache
    entry expires after ``ttl`` seconds, at which point a fresh JWKS
    is fetched on the next call.

    Attributes:
        ttl: Cache time-to-live in seconds.
    """

    def __init__(self, ttl: int = _DEFAULT_JWKS_CACHE_TTL) -> None:
        """Initialize with the given TTL."""
        self.ttl = ttl
        self._lock = threading.Lock()
        self._clients: dict[str, tuple[PyJWKClient, float]] = {}

    def get_client(self, jwks_uri: str) -> PyJWKClient:
        """Get or create a cached PyJWKClient for the given JWKS URI.

        Args:
            jwks_uri: The JWKS endpoint URL.

        Returns:
            A :class:`PyJWKClient` instance.
        """
        now = time.monotonic()
        with self._lock:
            entry = self._clients.get(jwks_uri)
            if entry is not None:
                client, created_at = entry
                if now - created_at < self.ttl:
                    return client

            client = PyJWKClient(jwks_uri, cache_keys=True, lifespan=self.ttl)
            self._clients[jwks_uri] = (client, now)
            return client

    def clear(self) -> None:
        """Clear all cached clients."""
        with self._lock:
            self._clients.clear()


# Module-level singleton cache.
_jwks_cache = _JWKSCache()


def _fetch_jwks_uri(issuer: str, *, timeout: float = _FETCH_TIMEOUT) -> str | None:
    """Fetch the JWKS URI from the issuer's OIDC discovery document.

    Args:
        issuer: The OIDC issuer URL (e.g.
            ``https://token.actions.githubusercontent.com``).
        timeout: HTTP request timeout in seconds.

    Returns:
        The ``jwks_uri`` string, or ``None`` if discovery fails.
    """
    discovery_url = f'{issuer.rstrip("/")}/.well-known/openid-configuration'
    try:
        response = httpx.get(discovery_url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
        jwks_uri = data.get('jwks_uri')
        if not jwks_uri or not isinstance(jwks_uri, str):
            logger.warning(
                'jwks_discovery_missing_uri',
                issuer=issuer,
                discovery_url=discovery_url,
            )
            return None
        return jwks_uri
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning(
            'jwks_discovery_failed',
            issuer=issuer,
            discovery_url=discovery_url,
            error=str(exc),
        )
        return None


def verify_jwt_signature(
    token: str,
    issuer: str,
    *,
    audience: str = '',
    timeout: float = _FETCH_TIMEOUT,
) -> JWTVerificationResult:
    """Verify a JWT's cryptographic signature using the issuer's JWKS.

    Fetches the issuer's OIDC discovery document to find the JWKS URI,
    then uses PyJWT to verify the token's signature against the
    published public keys.

    If JWKS fetching fails (network error, issuer down), returns a
    result with ``fallback=True`` and ``verified=False`` so the caller
    can decide whether to accept structural-only validation.

    Args:
        token: The raw JWT string (``header.payload.signature``).
        issuer: The expected OIDC issuer URL.
        audience: Expected ``aud`` claim. If empty, audience is not
            validated (some CI tokens have no audience).
        timeout: HTTP timeout for JWKS/discovery fetches.

    Returns:
        A :class:`JWTVerificationResult`.
    """
    # Step 1: Discover the JWKS URI.
    jwks_uri = _fetch_jwks_uri(issuer, timeout=timeout)
    if jwks_uri is None:
        return JWTVerificationResult(
            issuer=issuer,
            error=f'Failed to fetch OIDC discovery for {issuer}',
            fallback=True,
        )

    # Step 2: Get a cached JWKS client.
    try:
        jwks_client = _jwks_cache.get_client(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except (jwt.PyJWKClientError, jwt.DecodeError, Exception) as exc:  # noqa: BLE001
        logger.warning(
            'jwks_key_fetch_failed',
            issuer=issuer,
            jwks_uri=jwks_uri,
            error=str(exc),
        )
        return JWTVerificationResult(
            issuer=issuer,
            error=f'Failed to fetch signing key from JWKS: {exc}',
            fallback=True,
        )

    # Step 3: Verify the token signature and decode claims.
    try:
        decode_options: dict[str, Any] = {}
        if not audience:
            decode_options['verify_aud'] = False

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=_SUPPORTED_ALGORITHMS,
            issuer=issuer,
            audience=audience if audience else None,
            options=decode_options if decode_options else None,  # type: ignore[arg-type]  # PyJWT accepts dict at runtime; stubs declare Options
        )

        logger.info(
            'jwt_signature_verified',
            issuer=issuer,
            sub=claims.get('sub', ''),
        )
        return JWTVerificationResult(
            verified=True,
            claims=claims,
            issuer=issuer,
        )
    except jwt.ExpiredSignatureError:
        return JWTVerificationResult(
            issuer=issuer,
            error='JWT signature valid but token has expired',
        )
    except jwt.InvalidIssuerError:
        return JWTVerificationResult(
            issuer=issuer,
            error=f'JWT issuer does not match expected: {issuer}',
        )
    except jwt.InvalidSignatureError:
        return JWTVerificationResult(
            issuer=issuer,
            error='JWT cryptographic signature is invalid (possible forgery)',
        )
    except jwt.DecodeError as exc:
        return JWTVerificationResult(
            issuer=issuer,
            error=f'JWT decode error: {exc}',
        )
    except jwt.InvalidTokenError as exc:
        return JWTVerificationResult(
            issuer=issuer,
            error=f'JWT validation error: {exc}',
        )


def clear_jwks_cache() -> None:
    """Clear the module-level JWKS cache.

    Useful in tests or when rotating keys.
    """
    _jwks_cache.clear()


__all__ = [
    'JWTVerificationResult',
    'clear_jwks_cache',
    'verify_jwt_signature',
]
