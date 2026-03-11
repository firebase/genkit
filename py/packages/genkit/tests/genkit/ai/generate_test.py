#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import json
import pathlib
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, cast

import pytest
import yaml
from pydantic import BaseModel, TypeAdapter

from genkit import ActionKind, Document, Genkit, Message, ModelResponse, ModelResponseChunk
from genkit._ai._generate import generate_action
from genkit._ai._model import text_from_content, text_from_message
from genkit._ai._testing import (
    ProgrammableModel,
    define_echo_model,
    define_programmable_model,
)
from genkit._core._model import ModelRequest
from genkit._core._typing import (
    DocumentPart,
    FinishReason,
    GenerateActionOptions,
    Metadata,
    Part,
    Role,
    TextPart,
    ToolChoice,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)
from genkit.middleware import BaseMiddleware, GenerateParams, ModelParams, ToolParams


def _to_dict(obj: object) -> object:
    """Convert object to dict for test comparisons."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def _to_json(obj: object, indent: int | None = None) -> str:
    """Convert object to JSON string for test output."""
    if isinstance(obj, BaseModel):
        return obj.model_dump_json(indent=indent)
    return json.dumps(obj, indent=indent)


@pytest.fixture
def setup_test() -> tuple[Genkit, ProgrammableModel]:
    """Setup the test."""
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool(name='testTool')
    async def test_tool() -> object:
        """description"""  # noqa: D403, D415
        return 'tool called'

    return (ai, pm)


@pytest.mark.asyncio
async def test_simple_text_generate_request(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """Test that the generate action can generate text."""
    ai, pm = setup_test

    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(TextPart(text='bye'))]),
        )
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
        ),
    )

    assert response.text == 'bye'


@pytest.mark.asyncio
async def test_simulates_doc_grounding(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """Test that docs are correctly grounded and injected into prompt."""
    ai, pm = setup_test

    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(TextPart(text='bye'))]),
        )
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
            docs=[Document(content=[DocumentPart(TextPart(text='doc content 1'))])],
        ),
    )

    assert response.request is not None
    assert response.request.messages is not None
    assert response.request.messages[0] == Message(
        role=Role.USER,
        content=[
            Part(TextPart(text='hi')),
            Part(
                TextPart(
                    text='\n\nUse the following information to complete your task:' + '\n\n- [0]: doc content 1\n\n',
                    metadata=Metadata(root={'purpose': 'context'}),
                )
            ),
        ],
    )


class WrapGenerateRecordMiddleware(BaseMiddleware):
    """Records which iterations wrap_generate saw (for multi-turn tests)."""

    def __init__(self) -> None:
        self.iterations_seen: list[int] = []

    async def wrap_generate(
        self, params: GenerateParams, next_fn: Callable[[GenerateParams], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        self.iterations_seen.append(params.iteration)
        return await next_fn(params)


class WrapGenerateMiddleware(BaseMiddleware):
    """User journey: wrap each generate iteration to observe/modify the flow."""

    async def wrap_generate(
        self, params: GenerateParams, next_fn: Callable[[GenerateParams], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        # Modify request so the response reflects that wrap_generate ran
        msgs = list(params.request.messages)
        if msgs:
            last = msgs[-1]
            txt = text_from_message(last)
            marked = Message(
                role=last.role,
                content=[Part(TextPart(text=f'{txt} [iter {params.iteration}]'))],
            )
            msgs[-1] = marked
        new_params = GenerateParams(
            options=params.options,
            request=ModelRequest(messages=msgs),
            iteration=params.iteration,
        )
        return await next_fn(new_params)


class WrapToolMiddleware(BaseMiddleware):
    """User journey: wrap each tool execution to transform tool output before the model sees it."""

    async def wrap_tool(
        self,
        params: ToolParams,
        next_fn: Callable[[ToolParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> tuple[Part | None, Part | None]:
        resp_part, interrupt = await next_fn(params)
        if resp_part is None or not isinstance(resp_part.root, ToolResponsePart):
            return (resp_part, interrupt)
        orig = resp_part.root.tool_response.output
        wrapped = f'[WRAPPED] {orig}'
        new_resp = Part(
            ToolResponsePart(
                tool_response=ToolResponse(
                    name=resp_part.root.tool_response.name,
                    ref=resp_part.root.tool_response.ref,
                    output=wrapped,
                )
            )
        )
        return (new_resp, interrupt)


class OrderedMiddleware(BaseMiddleware):
    """Adds a marker so chain order can be asserted: first-in-list = outermost."""

    def __init__(self, marker: str) -> None:
        self.marker = marker

    async def wrap_model(
        self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        txt = ''.join(text_from_message(m) for m in params.request.messages)
        new_req = ModelRequest(
            messages=[Message(role=Role.USER, content=[Part(TextPart(text=f'{self.marker}{txt}'))])]
        )
        resp = await next_fn(ModelParams(request=new_req, on_chunk=params.on_chunk, context=params.context))
        assert resp.message is not None
        out_txt = text_from_message(resp.message)
        return ModelResponse(
            finish_reason=resp.finish_reason,
            message=Message(role=Role.USER, content=[Part(TextPart(text=f'{out_txt}{self.marker}'))]),
        )


class PreMiddleware(BaseMiddleware):
    async def wrap_model(self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]) -> ModelResponse:
        txt = ''.join(text_from_message(m) for m in params.request.messages)
        new_req = ModelRequest(messages=[Message(role=Role.USER, content=[Part(TextPart(text=f'PRE {txt}'))])])
        return await next_fn(ModelParams(request=new_req, on_chunk=params.on_chunk, context=params.context))


class PostMiddleware(BaseMiddleware):
    async def wrap_model(self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]) -> ModelResponse:
        resp: ModelResponse = await next_fn(params)
        assert resp.message is not None
        txt = text_from_message(resp.message)
        return ModelResponse(
            finish_reason=resp.finish_reason,
            message=Message(role=Role.USER, content=[Part(TextPart(text=f'{txt} POST'))]),
        )


@pytest.mark.asyncio
async def test_generate_wrap_generate_modifies_request_per_iteration(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """wrap_generate runs each iteration; modifying params affects what the model sees."""
    ai, *_ = setup_test
    define_echo_model(ai)

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[Message(role=Role.USER, content=[Part(TextPart(text='hi'))])],
        ),
        middleware=[WrapGenerateMiddleware()],
    )

    assert 'iter 0' in (response.text or '')


@pytest.mark.asyncio
async def test_generate_wrap_generate_runs_each_tool_loop_iteration(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """wrap_generate runs for every turn, including recursion when tools are resolved."""
    ai, pm = setup_test
    tool_request_msg = Message(
        role=Role.MODEL,
        content=[
            Part(
                ToolRequestPart(
                    tool_request=ToolRequest(input={}, name='testTool', ref='123'),
                )
            ),
        ],
    )
    pm.responses.append(
        ModelResponse(finish_reason=FinishReason.STOP, message=tool_request_msg),
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(TextPart(text='done'))]),
        ),
    )

    recorder = WrapGenerateRecordMiddleware()
    await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[Message(role=Role.USER, content=[Part(TextPart(text='hi'))])],
            tools=['testTool'],
            tool_choice=ToolChoice.REQUIRED,
        ),
        middleware=[recorder],
    )

    assert recorder.iterations_seen == [0, 1]


@pytest.mark.asyncio
async def test_generate_wrap_tool_transforms_tool_output(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """wrap_tool runs per tool call; modified output is what the model receives."""
    ai, pm = setup_test
    tool_request_msg = Message(
        role=Role.MODEL,
        content=[
            Part(
                ToolRequestPart(
                    tool_request=ToolRequest(input={}, name='testTool', ref='123'),
                )
            ),
        ],
    )
    pm.responses.append(
        ModelResponse(finish_reason=FinishReason.STOP, message=tool_request_msg),
    )
    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(TextPart(text='done'))]),
        ),
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[Message(role=Role.USER, content=[Part(TextPart(text='hi'))])],
            tools=['testTool'],
            tool_choice=ToolChoice.REQUIRED,
        ),
        middleware=[WrapToolMiddleware()],
    )

    assert response.request is not None and response.request.messages is not None
    tool_resp_msgs = [m for m in response.request.messages if m.role == Role.TOOL]
    assert len(tool_resp_msgs) >= 1
    tool_part = next(
        p.root for m in tool_resp_msgs for p in m.content if isinstance(p.root, ToolResponsePart)
    )
    assert tool_part.tool_response.output == '[WRAPPED] tool called'


@pytest.mark.asyncio
async def test_generate_wrap_model_transforms_request_and_response(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """wrap_model runs per model call; middleware can transform request and response."""
    ai, *_ = setup_test
    define_echo_model(ai)

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[PreMiddleware(), PostMiddleware()],
    )

    assert response.text == '[ECHO] user: "PRE hi" POST'


@pytest.mark.asyncio
async def test_generate_middleware_chain_order(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """First middleware in list is outermost: runs first on request, last on response."""
    ai, *_ = setup_test
    define_echo_model(ai)

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[Message(role=Role.USER, content=[Part(TextPart(text='hi'))])],
        ),
        middleware=[OrderedMiddleware('1'), OrderedMiddleware('2'), OrderedMiddleware('3')],
    )

    # Request: 1 (outermost) runs first → "1hi"; 2 → "21hi"; 3 (innermost) → "321hi"
    # Response: 3 appends first, 2, 1 last → suffix "321"
    assert response.text is not None
    assert '321hi' in response.text
    assert response.text.endswith('321')


@pytest.mark.asyncio
async def test_generate_middleware_next_fn_args_optional(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """Can call next function without args (convenience)."""
    ai, *_ = setup_test
    define_echo_model(ai)

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[PostMiddleware()],
    )

    assert response.text == '[ECHO] user: "hi" POST'


class AddContextMiddleware(BaseMiddleware):
    async def wrap_model(self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]) -> ModelResponse:
        new_context = {**params.context, 'banana': True}
        return await next_fn(ModelParams(request=params.request, on_chunk=params.on_chunk, context=new_context))


class InjectContextMiddleware(BaseMiddleware):
    async def wrap_model(self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]) -> ModelResponse:
        txt = ''.join(text_from_message(m) for m in params.request.messages)
        new_req = ModelRequest(
            messages=[Message(role=Role.USER, content=[Part(TextPart(text=f'{txt} {params.context}'))])],
        )
        return await next_fn(ModelParams(request=new_req, on_chunk=params.on_chunk, context=params.context))


@pytest.mark.asyncio
async def test_generate_middleware_can_modify_context(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """Test that middleware can modify context."""
    ai, *_ = setup_test
    define_echo_model(ai)

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='echoModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[AddContextMiddleware(), InjectContextMiddleware()],
        context={'foo': 'bar'},
    )

    assert response.text == '''[ECHO] user: "hi {'foo': 'bar', 'banana': True}"'''


class ModifyStreamMiddleware(BaseMiddleware):
    async def wrap_model(self, params: ModelParams, next_fn: Callable[[ModelParams], Awaitable[ModelResponse]]) -> ModelResponse:
        on_chunk = params.on_chunk
        if on_chunk:
            on_chunk(
                ModelResponseChunk(
                    role=Role.MODEL,
                    content=[Part(TextPart(text='something extra before'))],
                )
            )

        def chunk_handler(chunk: ModelResponseChunk) -> None:
            if on_chunk:
                on_chunk(
                    ModelResponseChunk(
                        role=Role.MODEL,
                        content=[Part(TextPart(text=f'intercepted: {text_from_content(chunk.content)}'))],
                    )
                )

        resp = await next_fn(ModelParams(request=params.request, on_chunk=chunk_handler, context=params.context))
        if on_chunk:
            on_chunk(
                ModelResponseChunk(
                    role=Role.MODEL,
                    content=[Part(TextPart(text='something extra after'))],
                )
            )
        return resp


@pytest.mark.asyncio
async def test_generate_middleware_can_modify_stream(
    setup_test: tuple[Genkit, ProgrammableModel],
) -> None:
    """Test that middleware can modify streams."""
    ai, pm = setup_test

    pm.responses.append(
        ModelResponse(
            finish_reason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[Part(TextPart(text='bye'))]),
        )
    )
    pm.chunks = [
        [
            ModelResponseChunk(role=Role.MODEL, content=[Part(TextPart(text='1'))]),
            ModelResponseChunk(role=Role.MODEL, content=[Part(TextPart(text='2'))]),
            ModelResponseChunk(role=Role.MODEL, content=[Part(TextPart(text='3'))]),
        ]
    ]

    got_chunks = []

    def collect_chunks(c: ModelResponseChunk) -> None:
        got_chunks.append(text_from_content(c.content))

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(TextPart(text='hi'))],
                ),
            ],
        ),
        middleware=[ModifyStreamMiddleware()],
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
spec_path = pathlib.Path(__file__).parent / '../../../../../../tests/specs/generate.yaml'
with spec_path.resolve().open() as stream:
    tests_spec = yaml.safe_load(stream)
    specs = tests_spec['tests']
    specs = [x for x in tests_spec['tests'] if x['name'] == 'calls tools']


@pytest.mark.parametrize(
    'spec',
    specs,
)
@pytest.mark.asyncio
async def test_generate_action_spec(spec: dict[str, Any]) -> None:
    """Run tests based on external generate action specifications."""
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool(name='testTool')
    async def test_tool() -> object:
        """description"""  # noqa: D403, D415
        return 'tool called'

    if 'modelResponses' in spec:
        pm.responses = [TypeAdapter(ModelResponse).validate_python(resp) for resp in spec['modelResponses']]

    if 'streamChunks' in spec:
        pm.chunks = []
        for stream_chunks in spec['streamChunks']:
            converted = []
            if stream_chunks:
                for chunk in stream_chunks:
                    converted.append(TypeAdapter(ModelResponseChunk).validate_python(chunk))
            pm.chunks.append(converted)

    action = await ai.registry.resolve_action(kind=ActionKind.UTIL, name='generate')
    assert action is not None

    response = None
    chunks: list[ModelResponseChunk] | None = None
    if spec.get('stream'):
        chunks = []
        captured_chunks = chunks  # Capture list reference for closure

        def on_chunk(chunk: ModelResponseChunk) -> None:
            captured_chunks.append(chunk)

        action_response = await action.run(
            ai.registry,
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),  # type: ignore[arg-type]
            on_chunk=on_chunk,  # type: ignore[misc]
        )
        response = action_response.response
    else:
        action_response = await action.run(
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),
        )
        response = action_response.response

    if 'expectChunks' in spec:
        got = clean_schema(chunks)
        want = clean_schema(spec['expectChunks'])
        assert isinstance(got, list) and isinstance(want, list)
        if not is_equal_lists(got, want):
            raise AssertionError(
                f'{_to_json(got, indent=2)}\n\nis not equal to expected:\n\n{_to_json(want, indent=2)}'
            )

    if 'expectResponse' in spec:
        got = clean_schema(_to_dict(response))
        want = clean_schema(spec['expectResponse'])
        if got != want:
            raise AssertionError(
                f'{_to_json(got, indent=2)}\n\nis not equal to expected:\n\n{_to_json(want, indent=2)}'
            )


def is_equal_lists(a: Sequence[object], b: Sequence[object]) -> bool:
    """Deep compare two lists of actions."""
    if len(a) != len(b):
        return False

    return all(_to_dict(a[i]) == _to_dict(b[i]) for i in range(len(a)))


primitives = (bool, str, int, float, type(None))


def is_primitive(obj: object) -> bool:
    """Check if an object is a primitive type."""
    return isinstance(obj, primitives)


def clean_schema(d: object) -> object:
    """Remove $schema keys and other non-relevant parts from a dict recursively."""
    if is_primitive(d):
        return d
    if isinstance(d, dict):
        out: dict[str, object] = {}
        d_dict = cast(dict[str, object], d)
        for key in d_dict:
            # Skip $schema and latencyMs (dynamic value that varies between runs)
            if key not in ('$schema', 'latencyMs'):
                out[key] = clean_schema(d_dict[key])
        return out
    elif isinstance(d, (list, tuple)):
        return [clean_schema(i) for i in d]
    else:
        return d
