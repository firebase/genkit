#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pathlib

import pytest
import yaml
from pydantic import TypeAdapter

from genkit.ai import ActionKind, Genkit
from genkit.blocks.generate import generate_action
from genkit.blocks.model import text_from_content, text_from_message
from genkit.codec import dump_dict, dump_json
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    DocumentData,
    DocumentPart,
    FinishReason,
    GenerateActionOptions,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Metadata,
    Part,
    Role,
    TextPart,
)
from genkit.testing import (
    define_echo_model,
    define_programmable_model,
)


@pytest.fixture
def setup_test():
    """Setup the test."""
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool(name='testTool')
    def test_tool():
        """description"""  # noqa: D400, D403, D415
        return 'tool called'

    return (ai, pm)


@pytest.mark.asyncio
async def test_simple_text_generate_request(setup_test) -> None:
    """Test that the generate action can generate text."""
    ai, pm = setup_test

    pm.responses.append(
        GenerateResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='bye'))]),
        )
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
        ),
    )

    assert response.text == 'bye'


@pytest.mark.asyncio
async def test_simulates_doc_grounding(setup_test) -> None:
    """Test that docs are correctly grounded and injected into prompt."""
    ai, pm = setup_test

    pm.responses.append(
        GenerateResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='bye'))]),
        )
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
            docs=[DocumentData(content=[DocumentPart(root=TextPart(text='doc content 1'))])],
        ),
    )

    assert response.request is not None
    assert response.request.messages is not None
    assert response.request.messages[0] == Message(
        role=Role.USER,
        content=[
            Part(root=TextPart(text='hi')),
            Part(
                root=TextPart(
                    text='\n\nUse the following information to complete your task:' + '\n\n- [0]: doc content 1\n\n',
                    metadata=Metadata(root={'purpose': 'context'}),
                )
            ),
        ],
    )


@pytest.mark.asyncio
async def test_generate_applies_middleware(
    setup_test,
) -> None:
    """When middleware is provided, apply it."""
    ai, *_ = setup_test
    define_echo_model(ai)

    async def pre_middle(req, ctx, next):
        txt = ''.join(text_from_message(m) for m in req.messages)
        return await next(
            GenerateRequest(
                messages=[
                    Message(role=Role.USER, content=[Part(root=TextPart(text=f'PRE {txt}'))]),
                ],
            ),
            ctx,
        )

    async def post_middle(req, ctx, next):
        resp: GenerateResponse = await next(req, ctx)
        txt = text_from_message(resp.message)
        return GenerateResponse(
            finish_reason=resp.finish_reason,
            message=Message(role=Role.USER, content=[Part(root=TextPart(text=f'{txt} POST'))]),
        )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[pre_middle, post_middle],
    )

    assert response.text == '[ECHO] user: "PRE hi" POST'


@pytest.mark.asyncio
async def test_generate_middleware_next_fn_args_optional(
    setup_test,
) -> None:
    """Can call next function without args (convenience)."""
    ai, *_ = setup_test
    define_echo_model(ai)

    async def post_middle(_, __, next):
        resp: GenerateResponse = await next()
        txt = text_from_message(resp.message)
        return GenerateResponse(
            finish_reason=resp.finish_reason,
            message=Message(role=Role.USER, content=[Part(root=TextPart(text=f'{txt} POST'))]),
        )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[post_middle],
    )

    assert response.text == '[ECHO] user: "hi" POST'


@pytest.mark.asyncio
async def test_generate_middleware_can_modify_context(
    setup_test,
) -> None:
    """Test that middleware can modify context."""
    ai, *_ = setup_test
    define_echo_model(ai)

    async def add_context(req, ctx, next):
        return await next(req, ActionRunContext(context={**ctx.context, 'banana': True}))

    async def inject_context(req, ctx, next):
        txt = ''.join(text_from_message(m) for m in req.messages)
        return await next(
            GenerateRequest(
                messages=[
                    Message(
                        role=Role.USER,
                        content=[Part(root=TextPart(text=f'{txt} {ctx.context}'))],
                    ),
                ],
            ),
            ctx,
        )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[add_context, inject_context],
        context={'foo': 'bar'},
    )

    assert response.text == '''[ECHO] user: "hi {'foo': 'bar', 'banana': True}"'''


@pytest.mark.asyncio
async def test_generate_middleware_can_modify_stream(
    setup_test,
) -> None:
    """Test that middleware can modify streams."""
    ai, pm = setup_test

    pm.responses.append(
        GenerateResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='bye'))]),
        )
    )
    pm.chunks = [
        [
            GenerateResponseChunk(role=Role.MODEL, content=[Part(root=TextPart(text='1'))]),
            GenerateResponseChunk(role=Role.MODEL, content=[Part(root=TextPart(text='2'))]),
            GenerateResponseChunk(role=Role.MODEL, content=[Part(root=TextPart(text='3'))]),
        ]
    ]

    async def modify_stream(req, ctx, next):
        ctx.send_chunk(
            GenerateResponseChunk(
                role=Role.MODEL,
                content=[Part(root=TextPart(text='something extra before'))],
            )
        )

        def chunk_handler(chunk):
            ctx.send_chunk(
                GenerateResponseChunk(
                    role=Role.MODEL,
                    content=[Part(root=TextPart(text=f'intercepted: {text_from_content(chunk.content)}'))],
                )
            )

        resp = await next(req, ActionRunContext(context=ctx.context, on_chunk=chunk_handler))
        ctx.send_chunk(
            GenerateResponseChunk(
                role=Role.MODEL,
                content=[Part(root=TextPart(text='something extra after'))],
            )
        )
        return resp

    got_chunks = []

    def collect_chunks(c):
        got_chunks.append(text_from_content(c.content))

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[modify_stream],
        on_chunk=collect_chunks,
    )

    assert response.text == 'bye'
    assert got_chunks == [
        'something extra before',
        'intercepted: 1',
        'intercepted: 2',
        'intercepted: 3',
        'something extra after',
    ]


##########################################################################
# run tests from /tests/specs/generate.yaml
##########################################################################

specs = []
with open(pathlib.Path(__file__).parent.joinpath('../../../../../../tests/specs/generate.yaml').resolve()) as stream:
    tests_spec = yaml.safe_load(stream)
    specs = tests_spec['tests']
    specs = [x for x in tests_spec['tests'] if x['name'] == 'calls tools']


@pytest.mark.parametrize(
    'spec',
    specs,
)
@pytest.mark.asyncio
async def test_generate_action_spec(spec) -> None:
    """Run tests based on external generate action specifications."""
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool(name='testTool')
    def test_tool():
        """description"""  # noqa: D400, D403, D415
        return 'tool called'

    if 'modelResponses' in spec:
        pm.responses = [TypeAdapter(GenerateResponse).validate_python(resp) for resp in spec['modelResponses']]

    if 'streamChunks' in spec:
        pm.chunks = []
        for chunks in spec['streamChunks']:
            converted = []
            for chunk in chunks:
                converted.append(TypeAdapter(GenerateResponseChunk).validate_python(chunk))
            pm.chunks.append(converted)

    action = await ai.registry.resolve_action(kind=ActionKind.UTIL, name='generate')
    assert action is not None

    response = None
    chunks = None
    if 'stream' in spec and spec['stream']:
        chunks = []

        def on_chunk(chunk):
            chunks.append(chunk)

        action_response = await action.arun(
            ai.registry,
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),  # type: ignore[arg-type]
            on_chunk=on_chunk,  # type: ignore[misc]
        )
        response = action_response.response
    else:
        action_response = await action.arun(
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),
        )
        response = action_response.response

    if 'expectChunks' in spec:
        got = clean_schema(chunks)
        want = clean_schema(spec['expectChunks'])
        if not is_equal_lists(got, want):
            raise AssertionError(
                f'{dump_json(got, indent=2)}\n\nis not equal to expected:\n\n{dump_json(want, indent=2)}'
            )

    if 'expectResponse' in spec:
        got = clean_schema(dump_dict(response))
        want = clean_schema(spec['expectResponse'])
        if got != want:
            raise AssertionError(
                f'{dump_json(got, indent=2)}\n\nis not equal to expected:\n\n{dump_json(want, indent=2)}'
            )


def is_equal_lists(a, b):
    """Deep compare two lists of actions."""
    if len(a) != len(b):
        return False

    for i in range(len(a)):
        if dump_dict(a[i]) != dump_dict(b[i]):
            return False

    return True


primitives = (bool, str, int, float, type(None))


def is_primitive(obj):
    """Check if an object is a primitive type."""
    return isinstance(obj, primitives)


def clean_schema(d):
    """Remove $schema keys and other non-relevant parts from a dict recursively."""
    if is_primitive(d):
        return d
    if isinstance(d, dict):
        out = {}
        for key in d:
            if key != '$schema':
                out[key] = clean_schema(d[key])
        return out
    elif hasattr(d, '__len__'):
        return [clean_schema(i) for i in d]
    else:
        return d
