# Copyright 2025 Google LLC
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

"""Tests for genkit.core.context — api_key() context provider.

These tests mirror the JS SDK's core/tests/context_test.ts to ensure
behavioral parity across SDKs.
"""

from typing import Any

import pytest

from genkit.core.context import ApiKeyContext, api_key
from genkit.core.error import UserFacingError


def _request(key: str | None = None) -> dict[str, Any]:
    """Build a minimal request_data dict matching the flows server format.

    Args:
        key: Optional Authorization header value.

    Returns:
        Dict with method, headers, and input fields.
    """
    headers: dict[str, str] = {}
    if key is not None:
        headers['authorization'] = key
    return {
        'method': 'POST',
        'headers': headers,
        'input': {},
    }


# The flows server passes (context, request_data) to providers.
_EMPTY_CTX: dict[str, Any] = {}


class TestApiKeyPassthrough:
    """Tests for api_key() in pass-through mode (no argument)."""

    @pytest.mark.asyncio
    async def test_no_key_returns_none(self) -> None:
        """Pass-through with no Authorization header returns api_key=None."""
        provider = api_key()
        result = await provider(_EMPTY_CTX, _request())
        assert result == {'auth': {'api_key': None}}

    @pytest.mark.asyncio
    async def test_with_key_returns_key(self) -> None:
        """Pass-through with Authorization header returns the key."""
        provider = api_key()
        result = await provider(_EMPTY_CTX, _request('my-key'))
        assert result == {'auth': {'api_key': 'my-key'}}


class TestApiKeyExactMatch:
    """Tests for api_key('expected') in exact-match mode."""

    @pytest.mark.asyncio
    async def test_correct_key_succeeds(self) -> None:
        """Exact match with correct key returns the key."""
        provider = api_key('secret')
        result = await provider(_EMPTY_CTX, _request('secret'))
        assert result == {'auth': {'api_key': 'secret'}}

    @pytest.mark.asyncio
    async def test_wrong_key_raises_permission_denied(self) -> None:
        """Exact match with wrong key raises PERMISSION_DENIED."""
        provider = api_key('secret')
        with pytest.raises(UserFacingError, match='Permission Denied') as exc_info:
            await provider(_EMPTY_CTX, _request('wrong-key'))
        assert exc_info.value.status == 'PERMISSION_DENIED'

    @pytest.mark.asyncio
    async def test_missing_key_raises_unauthenticated(self) -> None:
        """Exact match with no key raises UNAUTHENTICATED."""
        provider = api_key('secret')
        with pytest.raises(UserFacingError, match='Unauthenticated') as exc_info:
            await provider(_EMPTY_CTX, _request())
        assert exc_info.value.status == 'UNAUTHENTICATED'

    @pytest.mark.asyncio
    async def test_empty_key_raises_unauthenticated(self) -> None:
        """Exact match with empty string key raises UNAUTHENTICATED."""
        provider = api_key('secret')
        with pytest.raises(UserFacingError, match='Unauthenticated') as exc_info:
            await provider(_EMPTY_CTX, _request(''))
        assert exc_info.value.status == 'UNAUTHENTICATED'


class TestApiKeyCustomPolicy:
    """Tests for api_key(policy_fn) in custom policy mode."""

    @pytest.mark.asyncio
    async def test_sync_policy_receives_context(self) -> None:
        """Sync policy function receives the correct ApiKeyContext."""
        captured: list[ApiKeyContext] = []

        def capture_policy(ctx: ApiKeyContext) -> None:
            captured.append(ctx)

        provider = api_key(capture_policy)
        result = await provider(_EMPTY_CTX, _request('test-key'))

        assert len(captured) == 1
        assert captured[0].auth == {'api_key': 'test-key'}
        assert result == {'auth': {'api_key': 'test-key'}}

    @pytest.mark.asyncio
    async def test_sync_policy_with_no_key(self) -> None:
        """Sync policy receives api_key=None when no header present."""
        captured: list[ApiKeyContext] = []

        def capture_policy(ctx: ApiKeyContext) -> None:
            captured.append(ctx)

        provider = api_key(capture_policy)
        await provider(_EMPTY_CTX, _request())

        assert len(captured) == 1
        assert captured[0].auth == {'api_key': None}

    @pytest.mark.asyncio
    async def test_sync_policy_can_raise(self) -> None:
        """Sync policy can reject requests by raising."""

        def deny_all(ctx: ApiKeyContext) -> None:
            raise UserFacingError('PERMISSION_DENIED', 'Denied')

        provider = api_key(deny_all)
        with pytest.raises(UserFacingError, match='Denied'):
            await provider(_EMPTY_CTX, _request('any-key'))

    @pytest.mark.asyncio
    async def test_async_policy_receives_context(self) -> None:
        """Async policy function receives the correct ApiKeyContext."""
        captured: list[ApiKeyContext] = []

        async def capture_policy(ctx: ApiKeyContext) -> None:
            captured.append(ctx)

        provider = api_key(capture_policy)
        result = await provider(_EMPTY_CTX, _request('async-key'))

        assert len(captured) == 1
        assert captured[0].auth == {'api_key': 'async-key'}
        assert result == {'auth': {'api_key': 'async-key'}}

    @pytest.mark.asyncio
    async def test_async_policy_can_raise(self) -> None:
        """Async policy can reject requests by raising."""

        async def deny_all(ctx: ApiKeyContext) -> None:
            raise UserFacingError('UNAUTHENTICATED', 'Must authenticate')

        provider = api_key(deny_all)
        with pytest.raises(UserFacingError, match='Must authenticate'):
            await provider(_EMPTY_CTX, _request('any-key'))


class TestApiKeyContext:
    """Tests for the ApiKeyContext dataclass."""

    def test_equality(self) -> None:
        """Two ApiKeyContext with the same key are equal."""
        ctx1 = ApiKeyContext('key')
        ctx2 = ApiKeyContext('key')
        assert ctx1 == ctx2

    def test_inequality(self) -> None:
        """Two ApiKeyContext with different keys are not equal."""
        ctx1 = ApiKeyContext('key1')
        ctx2 = ApiKeyContext('key2')
        assert ctx1 != ctx2

    def test_none_key(self) -> None:
        """ApiKeyContext with None key is valid."""
        ctx = ApiKeyContext(None)
        assert ctx.auth == {'api_key': None}
        assert ctx.to_dict() == {'auth': {'api_key': None}}

    def test_repr(self) -> None:
        """ApiKeyContext repr includes the auth dict."""
        ctx = ApiKeyContext('my-key')
        assert 'my-key' in repr(ctx)
        assert 'ApiKeyContext' in repr(ctx)

    def test_to_dict(self) -> None:
        """to_dict returns a plain dict suitable for context merging."""
        ctx = ApiKeyContext('k')
        assert ctx.to_dict() == {'auth': {'api_key': 'k'}}

    def test_inequality_with_other_type(self) -> None:
        """ApiKeyContext is not equal to a non-ApiKeyContext object."""
        ctx = ApiKeyContext('key')
        assert ctx != 'not-a-context'
