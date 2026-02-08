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


"""Tests for model middleware functions.

Covers extracted utilities (part_has_media, has_media_in_messages,
find_system_message_index, last_user_message, context_item_template)
and middleware factories (augment_with_context, retry, validate_support,
simulate_system_prompt, simulate_constrained_generation).
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from genkit.blocks.middleware import (
    DEFAULT_FALLBACK_STATUSES,
    DEFAULT_RETRY_STATUSES,
    augment_with_context,
    context_item_template,
    find_system_message_index,
    has_media_in_messages,
    last_user_message,
    part_has_media,
    retry,
    simulate_constrained_generation,
    simulate_system_prompt,
    validate_support,
)
from genkit.core.action import ActionRunContext
from genkit.core.error import GenkitError
from genkit.core.typing import (
    DocumentData,
    DocumentPart,
    GenerateRequest,
    GenerateResponse,
    Media,
    MediaPart,
    Message,
    Metadata,
    OutputConfig,
    Part,
    Role,
    Supports,
    TextPart,
    ToolDefinition,
)


def _make_text_part(text: str = 'Hello') -> Part:
    return Part(root=TextPart(text=text))


def _make_media_part(url: str = 'https://example.com/img.png', content_type: str = 'image/png') -> Part:
    return Part(root=MediaPart(media=Media(url=url, content_type=content_type)))


def _make_message(role: str = 'user', text: str = 'Hello') -> Message:
    return Message(role=role, content=[_make_text_part(text)])


def _make_request(
    messages: list[Message] | None = None,
    tools: list[ToolDefinition] | None = None,
    output: OutputConfig | None = None,
) -> GenerateRequest:
    """Create a minimal GenerateRequest for testing."""
    if messages is None:
        messages = [_make_message()]
    return GenerateRequest(messages=messages, tools=tools, output=output)


def _make_response(text: str = 'response') -> GenerateResponse:
    """Create a minimal GenerateResponse for testing."""
    return GenerateResponse(
        message=Message(
            role='model',
            content=[Part(root=TextPart(text=text))],
        ),
    )


def _make_ctx() -> ActionRunContext:
    """Create a minimal ActionRunContext for testing."""
    return ActionRunContext(context={})


async def _run_augmenter(req: GenerateRequest) -> GenerateRequest:
    """Helper to run the augment_with_context middleware and capture the request."""
    augmenter = augment_with_context()
    req_future: asyncio.Future[GenerateRequest] = asyncio.Future()

    async def next_fn(req: GenerateRequest, _: ActionRunContext) -> GenerateResponse:
        req_future.set_result(req)
        return GenerateResponse(message=Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]))

    await augmenter(req, ActionRunContext(), next_fn)
    return req_future.result()


# -- part_has_media --


def test_part_has_media_true_for_media_part() -> None:
    """Returns True for a Part containing a MediaPart."""
    got = part_has_media(_make_media_part())
    if got is not True:
        pytest.fail(f'part_has_media(media_part) = {got}, want True')


def test_part_has_media_false_for_text_part() -> None:
    """Returns False for a Part containing a TextPart."""
    got = part_has_media(_make_text_part())
    if got is not False:
        pytest.fail(f'part_has_media(text_part) = {got}, want False')


# -- has_media_in_messages --


def test_has_media_in_messages_true() -> None:
    """Returns True when at least one message contains media."""
    msgs = [
        Message(role='user', content=[_make_text_part(), _make_media_part()]),
    ]
    got = has_media_in_messages(msgs)
    if got is not True:
        pytest.fail(f'has_media_in_messages = {got}, want True')


def test_has_media_in_messages_false() -> None:
    """Returns False when no messages contain media."""
    msgs = [
        Message(role='user', content=[_make_text_part()]),
        Message(role='model', content=[_make_text_part('reply')]),
    ]
    got = has_media_in_messages(msgs)
    if got is not False:
        pytest.fail(f'has_media_in_messages = {got}, want False')


def test_has_media_in_messages_empty() -> None:
    """Returns False for empty message list."""
    got = has_media_in_messages([])
    if got is not False:
        pytest.fail(f'has_media_in_messages([]) = {got}, want False')


# -- find_system_message_index --


def test_find_system_message_index_found() -> None:
    """Returns the index of the first system message."""
    msgs = [
        _make_message('user', 'hi'),
        _make_message('system', 'instructions'),
        _make_message('user', 'hello'),
    ]
    got = find_system_message_index(msgs)
    want = 1
    if got != want:
        pytest.fail(f'find_system_message_index = {got}, want {want}')


def test_find_system_message_index_first_position() -> None:
    """Returns 0 when system message is first."""
    msgs = [
        _make_message('system', 'sys'),
        _make_message('user', 'hi'),
    ]
    got = find_system_message_index(msgs)
    if got != 0:
        pytest.fail(f'find_system_message_index = {got}, want 0')


def test_find_system_message_index_not_found() -> None:
    """Returns -1 when no system message exists."""
    msgs = [_make_message('user', 'hi')]
    got = find_system_message_index(msgs)
    if got != -1:
        pytest.fail(f'find_system_message_index = {got}, want -1')


def test_find_system_message_index_empty() -> None:
    """Returns -1 for empty message list."""
    got = find_system_message_index([])
    if got != -1:
        pytest.fail(f'find_system_message_index([]) = {got}, want -1')


# -- last_user_message --


def test_last_user_message_found() -> None:
    """Returns the last user message."""
    msgs = [
        _make_message('user', 'first'),
        _make_message('model', 'reply'),
        _make_message('user', 'second'),
    ]
    got = last_user_message(msgs)
    assert got is not None, 'last_user_message returned None, want Message'
    got_text = str(got.content[0].root.text)
    if got_text != 'second':
        pytest.fail(f'last_user_message text = {got_text!r}, want "second"')


def test_last_user_message_not_found() -> None:
    """Returns None when no user messages exist."""
    msgs = [_make_message('model', 'reply')]
    got = last_user_message(msgs)
    if got is not None:
        pytest.fail(f'last_user_message = {got}, want None')


def test_last_user_message_empty() -> None:
    """Returns None for empty list."""
    got = last_user_message([])
    if got is not None:
        pytest.fail(f'last_user_message([]) = {got}, want None')


# -- context_item_template --


def test_context_item_template_uses_index() -> None:
    """Uses the index as citation when no metadata ref/id."""
    doc = DocumentData(content=[DocumentPart(root=TextPart(text='hello world'))])
    got = context_item_template(doc, 0)
    want = '- [0]: hello world\n'
    if got != want:
        pytest.fail(f'context_item_template = {got!r}, want {want!r}')


def test_context_item_template_uses_metadata_ref() -> None:
    """Uses metadata 'ref' field as citation when available."""
    doc = DocumentData(
        content=[DocumentPart(root=TextPart(text='content'))],
        metadata={'ref': 'doc-1'},
    )
    got = context_item_template(doc, 5)
    want = '- [doc-1]: content\n'
    if got != want:
        pytest.fail(f'context_item_template = {got!r}, want {want!r}')


# -- augment_with_context --


@pytest.mark.asyncio
async def test_augment_with_context_ignores_no_docs() -> None:
    """Request passes through unchanged when no docs are present."""
    req = GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
    )
    transformed_req = await _run_augmenter(req)
    assert transformed_req == req


@pytest.mark.asyncio
async def test_augment_with_context_adds_docs_as_context() -> None:
    """Documents are rendered and appended to the last user message."""
    req = GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[Part(root=TextPart(text='hi'))]),
        ],
        docs=[
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 2'))]),
        ],
    )

    transformed_req = await _run_augmenter(req)

    assert transformed_req == GenerateRequest(
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
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 2'))]),
        ],
    )


@pytest.mark.asyncio
async def test_augment_with_context_should_not_modify_non_pending_part() -> None:
    """Non-pending context parts are left unchanged."""
    req = GenerateRequest(
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
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )
    transformed_req = await _run_augmenter(req)
    assert transformed_req == req


@pytest.mark.asyncio
async def test_augment_with_context_with_purpose_part() -> None:
    """Pending context parts are replaced with rendered documents."""
    req = GenerateRequest(
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
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )

    transformed_req = await _run_augmenter(req)

    assert transformed_req == GenerateRequest(
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
            DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))]),
        ],
    )


# -- retry --


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt() -> None:
    """Passes through on first successful call."""
    mw = retry(max_retries=3)
    next_fn = AsyncMock(return_value=_make_response())
    result = await mw(_make_request(), _make_ctx(), next_fn)

    got = next_fn.await_count
    want = 1
    if got != want:
        pytest.fail(f'next_fn call count = {got}, want {want}')
    assert result.message is not None, 'expected message in response, got None'


@pytest.mark.asyncio
async def test_retry_retries_on_transient_error() -> None:
    """Retries on UNAVAILABLE then succeeds."""
    mw = retry(max_retries=2, initial_delay_ms=1, no_jitter=True)
    next_fn = AsyncMock(
        side_effect=[
            GenkitError(message='unavailable', status='UNAVAILABLE'),
            _make_response('recovered'),
        ]
    )
    result = await mw(_make_request(), _make_ctx(), next_fn)

    got = next_fn.await_count
    want = 2
    if got != want:
        pytest.fail(f'next_fn call count = {got}, want {want}')
    assert result.message is not None, 'expected message in response, got None'
    got_text = str(result.message.content[0].root.text)
    if got_text != 'recovered':
        pytest.fail(f'response text = {got_text!r}, want "recovered"')


@pytest.mark.asyncio
async def test_retry_raises_on_non_retryable_status() -> None:
    """Raises immediately on non-retryable statuses."""
    mw = retry(max_retries=3, initial_delay_ms=1)
    next_fn = AsyncMock(side_effect=GenkitError(message='bad request', status='INVALID_ARGUMENT'))
    with pytest.raises(GenkitError) as exc_info:
        await mw(_make_request(), _make_ctx(), next_fn)

    got = exc_info.value.status
    want = 'INVALID_ARGUMENT'
    if got != want:
        pytest.fail(f'error status = {got!r}, want {want!r}')
    if next_fn.await_count != 1:
        pytest.fail(f'expected 1 call, got {next_fn.await_count}')


@pytest.mark.asyncio
async def test_retry_exhausts_all_attempts() -> None:
    """Raises after exhausting all retries."""
    mw = retry(max_retries=2, initial_delay_ms=1, no_jitter=True)
    next_fn = AsyncMock(side_effect=GenkitError(message='unavailable', status='UNAVAILABLE'))
    with pytest.raises(GenkitError) as exc_info:
        await mw(_make_request(), _make_ctx(), next_fn)

    got = exc_info.value.status
    want = 'UNAVAILABLE'
    if got != want:
        pytest.fail(f'error status = {got!r}, want {want!r}')
    # 1 initial + 2 retries = 3 total
    got_count = next_fn.await_count
    want_count = 3
    if got_count != want_count:
        pytest.fail(f'next_fn call count = {got_count}, want {want_count}')


@pytest.mark.asyncio
async def test_retry_calls_on_error_callback() -> None:
    """Calls on_error for each retry attempt."""
    errors: list[tuple[Exception, int]] = []

    def on_error(e: Exception, attempt: int) -> None:
        errors.append((e, attempt))

    mw = retry(max_retries=2, initial_delay_ms=1, no_jitter=True, on_error=on_error)
    next_fn = AsyncMock(
        side_effect=[
            GenkitError(message='fail1', status='UNAVAILABLE'),
            GenkitError(message='fail2', status='UNAVAILABLE'),
            _make_response(),
        ]
    )
    await mw(_make_request(), _make_ctx(), next_fn)

    got = len(errors)
    want = 2
    if got != want:
        pytest.fail(f'on_error call count = {got}, want {want}')
    if errors[0][1] != 1:
        pytest.fail(f'first on_error attempt = {errors[0][1]}, want 1')
    if errors[1][1] != 2:
        pytest.fail(f'second on_error attempt = {errors[1][1]}, want 2')


@pytest.mark.asyncio
async def test_retry_custom_statuses() -> None:
    """Respects custom status list."""
    mw = retry(
        max_retries=1,
        statuses=['NOT_FOUND'],
        initial_delay_ms=1,
        no_jitter=True,
    )
    next_fn = AsyncMock(
        side_effect=[
            GenkitError(message='not found', status='NOT_FOUND'),
            _make_response('found'),
        ]
    )
    result = await mw(_make_request(), _make_ctx(), next_fn)

    got = next_fn.await_count
    want = 2
    if got != want:
        pytest.fail(f'next_fn call count = {got}, want {want}')
    assert result.message is not None, 'expected message in response, got None'


@pytest.mark.asyncio
async def test_retry_non_genkit_error_is_retried() -> None:
    """Non-GenkitError exceptions are always retried."""
    mw = retry(max_retries=1, initial_delay_ms=1, no_jitter=True)
    next_fn = AsyncMock(
        side_effect=[
            ConnectionError('network fail'),
            _make_response('ok'),
        ]
    )
    result = await mw(_make_request(), _make_ctx(), next_fn)

    got = next_fn.await_count
    want = 2
    if got != want:
        pytest.fail(f'next_fn call count = {got}, want {want}')
    assert result.message is not None, 'expected message in response, got None'


# -- validate_support --


@pytest.mark.asyncio
async def test_validate_support_passes_when_supports_is_none() -> None:
    """No validation when supports is None."""
    mw = validate_support(name='test-model')
    next_fn = AsyncMock(return_value=_make_response())
    result = await mw(_make_request(), _make_ctx(), next_fn)
    assert result.message is not None, 'expected message in response, got None'


@pytest.mark.asyncio
async def test_validate_support_passes_when_all_supported() -> None:
    """No error when all features are marked supported."""
    mw = validate_support(
        name='test-model',
        supports=Supports(media=True, tools=True, multiturn=True),
    )
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request(
        messages=[
            _make_message('user', 'hi'),
            _make_message('model', 'hey'),
        ],
    )
    result = await mw(req, _make_ctx(), next_fn)
    assert result.message is not None, 'expected message in response, got None'


@pytest.mark.asyncio
async def test_validate_support_raises_on_unsupported_tools() -> None:
    """Raises INVALID_ARGUMENT when tools are provided but not supported."""
    mw = validate_support(
        name='test-model',
        supports=Supports(tools=False),
    )
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request(
        tools=[ToolDefinition(name='my_tool', description='A tool', input_schema={})],
    )
    with pytest.raises(GenkitError) as exc_info:
        await mw(req, _make_ctx(), next_fn)
    if 'tool use' not in str(exc_info.value):
        pytest.fail(f'expected "tool use" in error, got {exc_info.value!r}')


@pytest.mark.asyncio
async def test_validate_support_raises_on_unsupported_multiturn() -> None:
    """Raises INVALID_ARGUMENT when multiturn is not supported."""
    mw = validate_support(
        name='test-model',
        supports=Supports(multiturn=False),
    )
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request(
        messages=[
            _make_message('user', 'hi'),
            _make_message('model', 'hey'),
        ],
    )
    with pytest.raises(GenkitError) as exc_info:
        await mw(req, _make_ctx(), next_fn)
    if 'multiple messages' not in str(exc_info.value):
        pytest.fail(f'expected "multiple messages" in error, got {exc_info.value!r}')


@pytest.mark.asyncio
async def test_validate_support_raises_on_unsupported_media() -> None:
    """Raises INVALID_ARGUMENT when media is provided but not supported."""
    mw = validate_support(
        name='test-model',
        supports=Supports(media=False),
    )
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request(
        messages=[
            Message(role='user', content=[_make_media_part()]),
        ],
    )
    with pytest.raises(GenkitError) as exc_info:
        await mw(req, _make_ctx(), next_fn)
    if 'media' not in str(exc_info.value):
        pytest.fail(f'expected "media" in error, got {exc_info.value!r}')


# -- simulate_system_prompt --


@pytest.mark.asyncio
async def test_simulate_system_prompt_converts_system_message() -> None:
    """System message is converted to user + model exchange."""
    mw = simulate_system_prompt()
    captured_req: GenerateRequest | None = None

    async def next_fn(req: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        nonlocal captured_req
        captured_req = req
        return _make_response()

    req = _make_request(
        messages=[
            _make_message('system', 'Be helpful'),
            _make_message('user', 'Hello'),
        ],
    )
    await mw(req, _make_ctx(), next_fn)

    assert captured_req is not None, 'next_fn was not called'

    got_len = len(captured_req.messages)
    want_len = 3
    if got_len != want_len:
        pytest.fail(f'message count = {got_len}, want {want_len}')

    got_role_0 = captured_req.messages[0].role
    if got_role_0 != 'user':
        pytest.fail(f'messages[0].role = {got_role_0!r}, want "user"')

    got_text_0 = str(captured_req.messages[0].content[0].root.text)
    if 'SYSTEM INSTRUCTIONS' not in got_text_0:
        pytest.fail(f'expected "SYSTEM INSTRUCTIONS" in first part, got {got_text_0!r}')

    got_role_1 = captured_req.messages[1].role
    if got_role_1 != 'model':
        pytest.fail(f'messages[1].role = {got_role_1!r}, want "model"')

    got_ack = str(captured_req.messages[1].content[0].root.text)
    if got_ack != 'Understood.':
        pytest.fail(f'acknowledgement = {got_ack!r}, want "Understood."')

    got_role_2 = captured_req.messages[2].role
    if got_role_2 != 'user':
        pytest.fail(f'messages[2].role = {got_role_2!r}, want "user"')


@pytest.mark.asyncio
async def test_simulate_system_prompt_custom_preface_and_ack() -> None:
    """Custom preface and acknowledgement are used."""
    mw = simulate_system_prompt(preface='[SYS]: ', acknowledgement='OK.')
    captured_req: GenerateRequest | None = None

    async def next_fn(req: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        nonlocal captured_req
        captured_req = req
        return _make_response()

    req = _make_request(
        messages=[
            _make_message('system', 'rules'),
            _make_message('user', 'hi'),
        ],
    )
    await mw(req, _make_ctx(), next_fn)

    assert captured_req is not None, 'next_fn was not called'

    got_preface = str(captured_req.messages[0].content[0].root.text)
    if got_preface != '[SYS]: ':
        pytest.fail(f'preface = {got_preface!r}, want "[SYS]: "')

    got_ack = str(captured_req.messages[1].content[0].root.text)
    if got_ack != 'OK.':
        pytest.fail(f'acknowledgement = {got_ack!r}, want "OK."')


@pytest.mark.asyncio
async def test_simulate_system_prompt_no_system_message() -> None:
    """No system message means request passes through unchanged."""
    mw = simulate_system_prompt()
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request()
    result = await mw(req, _make_ctx(), next_fn)
    assert result.message is not None, 'expected message in response, got None'


# -- simulate_constrained_generation --


@pytest.mark.asyncio
async def test_simulate_constrained_generation_injects_schema() -> None:
    """Schema instructions are injected, constrained flag is cleared."""
    mw = simulate_constrained_generation()
    captured_req: GenerateRequest | None = None

    async def next_fn(req: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        nonlocal captured_req
        captured_req = req
        return _make_response()

    schema = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
    req = _make_request(
        output=OutputConfig(constrained=True, schema=schema),
    )
    await mw(req, _make_ctx(), next_fn)

    assert captured_req is not None, 'next_fn was not called'
    assert captured_req.output is not None, 'expected output in request, got None'
    if captured_req.output.constrained is not False:
        pytest.fail(f'output.constrained = {captured_req.output.constrained!r}, want False')
    if captured_req.output.schema is not None:
        pytest.fail(f'output.schema = {captured_req.output.schema!r}, want None')


@pytest.mark.asyncio
async def test_simulate_constrained_generation_no_schema_passes_through() -> None:
    """Without schema, request passes through unchanged."""
    mw = simulate_constrained_generation()
    next_fn = AsyncMock(return_value=_make_response())
    req = _make_request()
    result = await mw(req, _make_ctx(), next_fn)
    assert result.message is not None, 'expected message in response, got None'


@pytest.mark.asyncio
async def test_simulate_constrained_generation_custom_renderer() -> None:
    """Custom instructions renderer is used."""

    def custom_renderer(schema: dict[str, object]) -> str:
        return f'OUTPUT JSON: {json.dumps(schema)}'

    mw = simulate_constrained_generation(instructions_renderer=custom_renderer)
    captured_req: GenerateRequest | None = None

    async def next_fn(req: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        nonlocal captured_req
        captured_req = req
        return _make_response()

    schema = {'type': 'string'}
    req = _make_request(
        output=OutputConfig(constrained=True, schema=schema),
    )
    await mw(req, _make_ctx(), next_fn)

    assert captured_req is not None, 'next_fn was not called'
    assert captured_req.output is not None, 'expected output in request, got None'
    if captured_req.output.constrained is not False:
        pytest.fail(f'output.constrained = {captured_req.output.constrained!r}, want False')


# -- default status lists --


def test_retry_statuses_match_js() -> None:
    """Default retry statuses match the JS canonical implementation."""
    want = [
        'UNAVAILABLE',
        'DEADLINE_EXCEEDED',
        'RESOURCE_EXHAUSTED',
        'ABORTED',
        'INTERNAL',
    ]
    got = DEFAULT_RETRY_STATUSES
    if got != want:
        pytest.fail(f'DEFAULT_RETRY_STATUSES = {got!r}, want {want!r}')


def test_fallback_statuses_match_js() -> None:
    """Default fallback statuses match the JS canonical implementation."""
    want = [
        'UNAVAILABLE',
        'DEADLINE_EXCEEDED',
        'RESOURCE_EXHAUSTED',
        'ABORTED',
        'INTERNAL',
        'NOT_FOUND',
        'UNIMPLEMENTED',
    ]
    got = DEFAULT_FALLBACK_STATUSES
    if got != want:
        pytest.fail(f'DEFAULT_FALLBACK_STATUSES = {got!r}, want {want!r}')
