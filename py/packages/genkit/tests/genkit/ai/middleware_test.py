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


"""Tests for the middleware module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from genkit import Document, Message, ModelResponse, Supports
from genkit._core._error import GenkitError, StatusName
from genkit._core._middleware import _fallback_for_registry as fallback
from genkit._core._typing import (
    DocumentPart,
    Media,
    MediaPart,
    Metadata,
    ModelRequest,
    Part,
    Role,
    TextPart,
    ToolDefinition,
)
from genkit.middleware import (
    BaseMiddleware,
    ModelParams,
    augment_with_context,
    download_request_media,
    retry,
    simulate_system_prompt,
    validate_support,
)


async def _run_model_middleware(
    mw: BaseMiddleware,
    req: ModelRequest,
    *,
    response: ModelResponse | None = None,
) -> ModelRequest:
    """Run middleware.wrap_model and return the request passed to next_fn."""
    req_future: asyncio.Future[ModelRequest] = asyncio.Future()
    if response is None:
        response = ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    async def next_fn(params: ModelParams) -> ModelResponse:
        req_future.set_result(params.request)
        return response

    await mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)
    return req_future.result()


async def run_augmenter(req: ModelRequest) -> ModelRequest:
    """Helper to run the augment_with_context middleware."""
    response = ModelResponse(message=Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]))
    return await _run_model_middleware(augment_with_context(), req, response=response)


@pytest.mark.asyncio
async def test_augment_with_context_ignores_no_docs() -> None:
    """Test simple prompt rendering."""
    req = ModelRequest(
        messages=[
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
    )

    transformed_req = await run_augmenter(req)

    assert transformed_req == req


@pytest.mark.asyncio
async def test_augment_with_context_adds_docs_as_context() -> None:
    """Test simple prompt rendering."""
    req = ModelRequest(
        messages=[
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
        docs=[
            Document(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
            Document(content=[DocumentPart(root=TextPart(text='doc content 2'))]),
        ],
    )

    transformed_req = await run_augmenter(req)

    assert transformed_req == ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=TextPart(text='hi')),
                    Part(
                        root=TextPart(
                            text='\n\nUse the following information to complete '
                            + 'your task:\n\n'
                            + '- [0]: doc content 1\n'
                            + '- [1]: doc content 2\n\n',
                            metadata=Metadata(root={'purpose': 'context'}),
                        )
                    ),
                ],
            )
        ],
        docs=[
            Document(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
            Document(content=[DocumentPart(root=TextPart(text='doc content 2'))]),
        ],
    )


@pytest.mark.asyncio
async def test_augment_with_context_should_not_modify_non_pending_part() -> None:
    """Test simple prompt rendering."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(
                        root=TextPart(
                            text='this is already context',
                            metadata=Metadata(root={'purpose': 'context'}),
                        )
                    ),
                    Part(root=TextPart(text='hi')),
                ],
            ),
        ],
        docs=[
            Document(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )

    transformed_req = await run_augmenter(req)

    assert transformed_req == req


@pytest.mark.asyncio
async def test_augment_with_context_with_purpose_part() -> None:
    """Test simple prompt rendering."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(
                        root=TextPart(
                            text='insert context here',
                            metadata=Metadata(root={'purpose': 'context', 'pending': True}),
                        )
                    ),
                    Part(root=TextPart(text='hi')),
                ],
            ),
        ],
        docs=[
            Document(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )

    transformed_req = await run_augmenter(req)

    assert transformed_req == ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(
                        root=TextPart(
                            text='\n\nUse the following information to complete '
                            + 'your task:\n\n'
                            + '- [0]: doc content 1\n\n',
                            metadata=Metadata(root={'purpose': 'context'}),
                        )
                    ),
                    Part(root=TextPart(text='hi')),
                ],
            )
        ],
        docs=[
            Document(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )


# =============================================================================
# validate_support tests
# =============================================================================


async def run_validate_support(
    req: ModelRequest, name: str = 'test-model', supports: Supports | None = None
) -> ModelRequest:
    """Helper to run the validate_support middleware."""
    return await _run_model_middleware(validate_support(name, supports), req)


@pytest.mark.asyncio
async def test_validate_support_passes_when_no_supports() -> None:
    """Test that validation passes when supports is None."""
    req = ModelRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])],
    )
    result = await run_validate_support(req)
    assert result == req


@pytest.mark.asyncio
async def test_validate_support_rejects_media_when_not_supported() -> None:
    """Test that media is rejected when not supported."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[Part(root=MediaPart(media=Media(url='https://example.com/img.png')))],
            )
        ],
    )
    with pytest.raises(GenkitError) as exc_info:
        await run_validate_support(req, supports=Supports(media=False))
    assert 'does not support media' in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_support_rejects_tools_when_not_supported() -> None:
    """Test that tools are rejected when not supported."""
    req = ModelRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])],
        tools=[ToolDefinition(name='test_tool', description='A test tool', input_schema={})],
    )
    with pytest.raises(GenkitError) as exc_info:
        await run_validate_support(req, supports=Supports(tools=False))
    assert 'does not support tool use' in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_support_rejects_multiturn_when_not_supported() -> None:
    """Test that multiturn is rejected when not supported."""
    req = ModelRequest(
        messages=[
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
            Message(role=Role.MODEL, content=[Part(root=TextPart(text='hello'))]),
            Message(role=Role.USER, content=[Part(root=TextPart(text='how are you'))]),
        ],
    )
    with pytest.raises(GenkitError) as exc_info:
        await run_validate_support(req, supports=Supports(multiturn=False))
    assert 'does not support multiple messages' in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_support_rejects_system_role_when_not_supported() -> None:
    """Test that system role is rejected when not supported."""
    req = ModelRequest(
        messages=[
            Message(role=Role.SYSTEM, content=[Part(root=TextPart(text='be helpful'))]),
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
    )
    with pytest.raises(GenkitError) as exc_info:
        await run_validate_support(req, supports=Supports(system_role=False))
    assert 'does not support system role' in str(exc_info.value)


# =============================================================================
# simulate_system_prompt tests
# =============================================================================


async def run_simulate_system_prompt(
    req: ModelRequest, preface: str = 'SYSTEM INSTRUCTIONS:\n', acknowledgement: str = 'Understood.'
) -> ModelRequest:
    """Helper to run the simulate_system_prompt middleware."""
    return await _run_model_middleware(simulate_system_prompt(preface=preface, acknowledgement=acknowledgement), req)


@pytest.mark.asyncio
async def test_simulate_system_prompt_no_system_message() -> None:
    """Test that requests without system messages pass through unchanged."""
    req = ModelRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])],
    )
    result = await run_simulate_system_prompt(req)
    assert len(result.messages) == 1
    assert result.messages[0].role == Role.USER


@pytest.mark.asyncio
async def test_simulate_system_prompt_converts_system_message() -> None:
    """Test that system messages are converted to user+model pairs."""
    req = ModelRequest(
        messages=[
            Message(role=Role.SYSTEM, content=[Part(root=TextPart(text='be helpful'))]),
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
    )
    result = await run_simulate_system_prompt(req)

    assert len(result.messages) == 3
    # First message should be user with preface + system content
    assert result.messages[0].role == Role.USER
    assert result.messages[0].content[0].root.text == 'SYSTEM INSTRUCTIONS:\n'
    assert result.messages[0].content[1].root.text == 'be helpful'
    # Second message should be model acknowledgement
    assert result.messages[1].role == Role.MODEL
    assert result.messages[1].content[0].root.text == 'Understood.'
    # Third message is original user message
    assert result.messages[2].role == Role.USER
    assert result.messages[2].content[0].root.text == 'hi'


@pytest.mark.asyncio
async def test_simulate_system_prompt_custom_preface() -> None:
    """Test custom preface and acknowledgement."""
    req = ModelRequest(
        messages=[
            Message(role=Role.SYSTEM, content=[Part(root=TextPart(text='be helpful'))]),
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
    )
    result = await run_simulate_system_prompt(req, preface='INSTRUCTIONS: ', acknowledgement='Got it.')

    assert result.messages[0].content[0].root.text == 'INSTRUCTIONS: '
    assert result.messages[1].content[0].root.text == 'Got it.'


# =============================================================================
# retry tests
# =============================================================================


@pytest.mark.asyncio
async def test_retry_success_no_retry() -> None:
    """Test that successful calls don't retry."""
    call_count = 0

    async def next_fn(params: ModelParams) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    retry_mw = retry(max_retries=3)
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    result = await retry_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert call_count == 1
    assert result.message is not None
    assert result.message.content[0].root.text == 'ok'


@pytest.mark.asyncio
async def test_retry_retries_on_retryable_error() -> None:
    """Test that retryable errors trigger retry."""
    call_count = 0

    async def next_fn(params: ModelParams) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise GenkitError(status='UNAVAILABLE', message='service unavailable')
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    retry_mw = retry(max_retries=3, initial_delay_ms=1, jitter=False)
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    result = await retry_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert call_count == 3
    assert result.message is not None
    assert result.message.content[0].root.text == 'ok'


@pytest.mark.asyncio
async def test_retry_throws_after_max_retries() -> None:
    """Test that error is raised after max retries exceeded."""
    call_count = 0

    async def next_fn(params: ModelParams) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        raise GenkitError(status='UNAVAILABLE', message='service unavailable')

    retry_mw = retry(max_retries=2, initial_delay_ms=1, jitter=False)
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    with pytest.raises(GenkitError) as exc_info:
        await retry_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert call_count == 3  # initial + 2 retries
    assert exc_info.value.status == 'UNAVAILABLE'


@pytest.mark.asyncio
async def test_retry_no_retry_on_non_retryable_error() -> None:
    """Test that non-retryable errors don't trigger retry."""
    call_count = 0

    async def next_fn(params: ModelParams) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        raise GenkitError(status='INVALID_ARGUMENT', message='bad request')

    retry_mw = retry(max_retries=3, initial_delay_ms=1)
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    with pytest.raises(GenkitError) as exc_info:
        await retry_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert call_count == 1  # no retries
    assert exc_info.value.status == 'INVALID_ARGUMENT'


@pytest.mark.asyncio
async def test_retry_calls_on_error_callback() -> None:
    """Test that on_error callback is called on each retry."""
    errors: list[tuple[Exception, int]] = []

    def on_error(err: Exception, attempt: int) -> None:
        errors.append((err, attempt))

    call_count = 0

    async def next_fn(params: ModelParams) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise GenkitError(status='UNAVAILABLE', message='service unavailable')
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    retry_mw = retry(max_retries=3, initial_delay_ms=1, jitter=False, on_error=on_error)
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    await retry_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert len(errors) == 2
    assert errors[0][1] == 1  # first retry attempt
    assert errors[1][1] == 2  # second retry attempt


# =============================================================================
# fallback tests
# =============================================================================


class MockActionResult:  # noqa: B903
    """Mock action result."""

    def __init__(self, response: ModelResponse) -> None:
        self.response = response


class MockAction:
    """Mock action for fallback tests."""

    fail_status: StatusName

    def __init__(self, should_fail: bool = False, fail_status: StatusName = 'UNAVAILABLE') -> None:
        self.should_fail = should_fail
        self.fail_status = fail_status
        self.call_count = 0

    async def run(self, input: ModelRequest, context: dict | None = None, on_chunk: object = None) -> MockActionResult:
        self.call_count += 1
        if self.should_fail:
            raise GenkitError(status=self.fail_status, message='model failed')
        return MockActionResult(
            ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='fallback ok'))]))
        )


class MockRegistry:
    """Mock registry for fallback tests."""

    def __init__(self, models: dict[str, MockAction]) -> None:
        self.models = models

    async def resolve_model(self, name: str) -> MockAction | None:
        return self.models.get(name)


class MockGenkit:  # noqa: B903
    """Mock Genkit instance for fallback tests."""

    def __init__(self, registry: MockRegistry) -> None:
        self.registry = registry


@pytest.mark.asyncio
async def test_fallback_success_no_fallback() -> None:
    """Test that successful calls don't trigger fallback."""
    fallback_model = MockAction()
    mock_registry = MockRegistry({'fallback-model': fallback_model})
    MockGenkit(mock_registry)

    fallback_mw = fallback(mock_registry, models=['fallback-model'])  # type: ignore[arg-type]
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    async def next_fn(params: ModelParams) -> ModelResponse:
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='primary ok'))]))

    result = await fallback_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert result.message is not None
    assert result.message.content[0].root.text == 'primary ok'
    assert fallback_model.call_count == 0


@pytest.mark.asyncio
async def test_fallback_uses_fallback_on_error() -> None:
    """Test that fallback is used when primary fails."""
    fallback_model = MockAction(should_fail=False)
    mock_registry = MockRegistry({'fallback-model': fallback_model})
    MockGenkit(mock_registry)

    fallback_mw = fallback(mock_registry, models=['fallback-model'])  # type: ignore[arg-type]
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    async def next_fn(params: ModelParams) -> ModelResponse:
        raise GenkitError(status='UNAVAILABLE', message='primary failed')

    result = await fallback_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert result.message is not None
    assert result.message.content[0].root.text == 'fallback ok'
    assert fallback_model.call_count == 1


@pytest.mark.asyncio
async def test_fallback_tries_multiple_models() -> None:
    """Test that fallback tries multiple models in order."""
    fallback1 = MockAction(should_fail=True, fail_status='UNAVAILABLE')
    fallback2 = MockAction(should_fail=False)
    mock_registry = MockRegistry({'fallback1': fallback1, 'fallback2': fallback2})
    MockGenkit(mock_registry)

    fallback_mw = fallback(mock_registry, models=['fallback1', 'fallback2'])  # type: ignore[arg-type]
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    async def next_fn(params: ModelParams) -> ModelResponse:
        raise GenkitError(status='UNAVAILABLE', message='primary failed')

    result = await fallback_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert result.message is not None
    assert result.message.content[0].root.text == 'fallback ok'
    assert fallback1.call_count == 1
    assert fallback2.call_count == 1


@pytest.mark.asyncio
async def test_fallback_no_fallback_on_non_fallbackable_error() -> None:
    """Test that non-fallbackable errors don't trigger fallback."""
    fallback_model = MockAction()
    mock_registry = MockRegistry({'fallback-model': fallback_model})
    MockGenkit(mock_registry)

    fallback_mw = fallback(mock_registry, models=['fallback-model'])  # type: ignore[arg-type]
    req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))])])

    async def next_fn(params: ModelParams) -> ModelResponse:
        raise GenkitError(status='INVALID_ARGUMENT', message='bad request')

    with pytest.raises(GenkitError) as exc_info:
        await fallback_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    assert exc_info.value.status == 'INVALID_ARGUMENT'
    assert fallback_model.call_count == 0


# =============================================================================
# download_request_media tests
# =============================================================================


class MockHttpResponse:
    """Mock HTTP response for download tests."""

    def __init__(self, content: bytes, content_type: str = 'image/png') -> None:
        self.content = content
        self.headers = {'content-type': content_type}

    def raise_for_status(self) -> None:
        pass


@pytest.mark.asyncio
async def test_download_request_media_converts_http_url() -> None:
    """Test that HTTP URLs are downloaded and converted to data URIs."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=TextPart(text='What is this?')),
                    Part(root=MediaPart(media=Media(url='https://example.com/cat.png'))),
                ],
            )
        ],
    )

    download_mw = download_request_media()
    req_future: asyncio.Future[ModelRequest] = asyncio.Future()

    async def next_fn(params: ModelParams) -> ModelResponse:
        req_future.set_result(params.request)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = MockHttpResponse(b'fake image data', 'image/png')
        mock_client_class.return_value = mock_client

        await download_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    result = req_future.result()
    # First part should still be text
    assert result.messages[0].content[0].root.text == 'What is this?'
    # Second part should be converted to data URI
    media_part = result.messages[0].content[1].root
    assert isinstance(media_part, MediaPart)
    assert media_part.media.url.startswith('data:image/png;base64,')
    assert media_part.media.content_type == 'image/png'


@pytest.mark.asyncio
async def test_download_request_media_skips_data_uris() -> None:
    """Test that data URIs are not re-downloaded."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=MediaPart(media=Media(url='data:image/png;base64,abc123'))),
                ],
            )
        ],
    )

    download_mw = download_request_media()
    req_future: asyncio.Future[ModelRequest] = asyncio.Future()

    async def next_fn(params: ModelParams) -> ModelResponse:
        req_future.set_result(params.request)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        await download_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    result = req_future.result()
    # Should still have the original data URI
    media_part = result.messages[0].content[0].root
    assert isinstance(media_part, MediaPart)
    assert media_part.media.url == 'data:image/png;base64,abc123'
    # HTTP client should not have been called
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_download_request_media_respects_max_bytes() -> None:
    """Test that max_bytes truncates downloaded content."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[Part(root=MediaPart(media=Media(url='https://example.com/big.png')))],
            )
        ],
    )

    download_mw = download_request_media(max_bytes=10)
    req_future: asyncio.Future[ModelRequest] = asyncio.Future()

    async def next_fn(params: ModelParams) -> ModelResponse:
        req_future.set_result(params.request)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        # Return 100 bytes but we only want 10
        mock_client.get.return_value = MockHttpResponse(b'a' * 100, 'image/png')
        mock_client_class.return_value = mock_client

        await download_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    result = req_future.result()
    media_part = result.messages[0].content[0].root
    assert isinstance(media_part, MediaPart)
    # Decode the base64 and check length
    import base64

    data_uri = media_part.media.url
    # Extract base64 part after 'data:image/png;base64,'
    b64_part = data_uri.split(',')[1]
    decoded = base64.b64decode(b64_part)
    assert len(decoded) == 10


@pytest.mark.asyncio
async def test_download_request_media_with_filter() -> None:
    """Test that filter function can skip certain parts."""
    req = ModelRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(root=MediaPart(media=Media(url='https://example.com/skip.png'))),
                    Part(root=MediaPart(media=Media(url='https://example.com/download.png'))),
                ],
            )
        ],
    )

    # Filter that skips URLs containing 'skip'
    def filter_fn(part: Part) -> bool:
        if isinstance(part.root, MediaPart):
            return 'skip' not in part.root.media.url
        return True

    download_mw = download_request_media(filter_fn=filter_fn)
    req_future: asyncio.Future[ModelRequest] = asyncio.Future()

    async def next_fn(params: ModelParams) -> ModelResponse:
        req_future.set_result(params.request)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='ok'))]))

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = MockHttpResponse(b'image', 'image/png')
        mock_client_class.return_value = mock_client

        await download_mw.wrap_model(ModelParams(request=req, on_chunk=None, context={}), next_fn)

    result = req_future.result()
    # First part should still have HTTP URL (skipped)
    first_part = result.messages[0].content[0].root
    assert isinstance(first_part, MediaPart)
    assert first_part.media.url == 'https://example.com/skip.png'
    # Second part should be converted
    second_part = result.messages[0].content[1].root
    assert isinstance(second_part, MediaPart)
    assert second_part.media.url.startswith('data:image/png;base64,')
