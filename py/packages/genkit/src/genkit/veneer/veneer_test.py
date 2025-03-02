#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import json

import pytest
from genkit.ai.formats.types import FormatDef, Formatter, FormatterConfig
from genkit.ai.model import MessageWrapper
from genkit.ai.testing_utils import (
    EchoModel,
    ProgrammableModel,
    define_echo_model,
    define_programmable_model,
)
from genkit.core.typing import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Metadata,
    OutputConfig,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequest1,
    ToolRequestPart,
    ToolResponse1,
    ToolResponsePart,
)
from genkit.veneer.veneer import Genkit
from pydantic import BaseModel, Field

type SetupFixture = tuple[Genkit, EchoModel, ProgrammableModel]


@pytest.fixture
def setup_test():
    ai = Genkit(model='echoModel')

    pm, _ = define_programmable_model(ai)
    echo, _ = define_echo_model(ai)

    return (ai, echo, pm)


@pytest.mark.asyncio
async def test_generate_uses_default_model(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(prompt='hi', config={'temperature': 11})

    assert response.text == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_explicit_model(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        model='echoModel', prompt='hi', config={'temperature': 11}
    )

    assert response.text == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_str_prompt(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(prompt='hi', config={'temperature': 11})

    assert response.text == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_part_prompt(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        prompt=TextPart(text='hi'), config={'temperature': 11}
    )

    assert response.text == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_part_list_prompt(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        prompt=[TextPart(text='hello'), TextPart(text='world')],
        config={'temperature': 11},
    )

    assert response.text == '[ECHO] user: "hello","world" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_str_system(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system='talk like pirate', prompt='hi', config={'temperature': 11}
    )

    assert (
        response.text
        == '[ECHO] system: "talk like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_part_system(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system=TextPart(text='talk like pirate'),
        prompt='hi',
        config={'temperature': 11},
    )

    assert (
        response.text
        == '[ECHO] system: "talk like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_part_list_system(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system=[TextPart(text='talk'), TextPart(text='like pirate')],
        prompt='hi',
        config={'temperature': 11},
    )

    assert (
        response.text
        == '[ECHO] system: "talk","like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_messages(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text='hi')],
            ),
        ],
        config={'temperature': 11},
    )

    assert response.text == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_system_prompt_messages(
    setup_test: SetupFixture,
) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system='talk like pirate',
        prompt='hi again',
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text='hi')],
            ),
            Message(
                role=Role.MODEL,
                content=[TextPart(text='bye')],
            ),
        ],
    )

    assert (
        response.text
        == '[ECHO] system: "talk like pirate" user: "hi" model: "bye" user: "hi again"'
    )


@pytest.mark.asyncio
async def test_generate_with_tools(setup_test: SetupFixture) -> None:
    ai, echo, *_ = setup_test

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        tool_choice='required',
        tools=['testTool'],
    )

    assert response.text == '[ECHO] user: "hi" tool_choice=required'
    assert echo.last_request.tools == [
        ToolDefinition(
            name='testTool',
            description='the tool',
            input_schema={
                'properties': {
                    'value': {
                        'default': None,
                        'description': 'value field',
                        'title': 'Value',
                        'type': 'string',
                    }
                },
                'title': 'ToolInput',
                'type': 'object',
            },
            outputSchema={},
        )
    ]


@pytest.mark.asyncio
async def test_generate_with_tools(setup_test: SetupFixture) -> None:
    ai, _, pm, *_ = setup_test

    class ToolInput(BaseModel):
        value: int = Field(None, description='value field')

    @ai.tool('the tool', name='testTool')
    def test_tool(input: ToolInput):
        return 'abc'

    tool_request_msg = MessageWrapper(
        Message(
            role=Role.MODEL,
            content=[
                ToolRequestPart(
                    toolRequest=ToolRequest1(
                        input={'value': 5}, name='testTool', ref='123'
                    )
                )
            ],
        )
    )
    pm.responses.append(
        GenerateResponse(
            finishReason=FinishReason.STOP,
            message=tool_request_msg,
        )
    )
    pm.responses.append(
        GenerateResponse(
            finishReason=FinishReason.STOP,
            message=Message(
                role=Role.MODEL, content=[TextPart(text='tool called')]
            ),
        )
    )

    response = await ai.generate(
        model='programmableModel',
        prompt='hi',
        tool_choice='required',
        tools=['testTool'],
    )

    assert response.text == 'tool called'
    assert response.request.messages[0] == Message(
        role=Role.USER, content=[TextPart(text='hi')]
    )
    assert response.request.messages[1] == tool_request_msg
    assert response.request.messages[2] == Message(
        role=Role.TOOL,
        content=[
            ToolResponsePart(
                tool_response=ToolResponse1(
                    ref='123', name='testTool', output='abc'
                )
            )
        ],
    )
    assert pm.last_request.tools == [
        ToolDefinition(
            name='testTool',
            description='the tool',
            input_schema={
                'properties': {
                    'value': {
                        'default': None,
                        'description': 'value field',
                        'title': 'Value',
                        'type': 'integer',
                    }
                },
                'title': 'ToolInput',
                'type': 'object',
            },
            outputSchema={},
        )
    ]


@pytest.mark.asyncio
async def test_generate_with_output(setup_test: SetupFixture) -> None:
    ai, *_ = setup_test

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        output_constrained=True,
        output_format='json',
        output_content_type='application/json',
        output_schema=TestSchema,
        output_instructions=False,
    )

    assert response.request == GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[TextPart(text='hi')]),
        ],
        config={},
        tools=[],
        output=OutputConfig(
            format='json',
            schema_={
                'properties': {
                    'foo': {
                        'default': None,
                        'description': 'foo field',
                        'title': 'Foo',
                        'type': 'integer',
                    },
                    'bar': {
                        'default': None,
                        'description': 'bar field',
                        'title': 'Bar',
                        'type': 'string',
                    },
                },
                'title': 'TestSchema',
                'type': 'object',
            },
            constrained=True,
            content_type='application/json',
        ),
    )


@pytest.mark.asyncio
async def test_generate_defaults_to_json_format(
    setup_test: SetupFixture,
) -> None:
    """When output_schema is provided, format will default to json"""
    ai, *_ = setup_test

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        output_schema=TestSchema,
    )

    assert response.request == GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[TextPart(text='hi')]),
        ],
        config={},
        tools=[],
        output=OutputConfig(
            format='json',
            schema_={
                'properties': {
                    'foo': {
                        'default': None,
                        'description': 'foo field',
                        'title': 'Foo',
                        'type': 'integer',
                    },
                    'bar': {
                        'default': None,
                        'description': 'bar field',
                        'title': 'Bar',
                        'type': 'string',
                    },
                },
                'title': 'TestSchema',
                'type': 'object',
            },
            # these get populated by the format
            constrained=True,
            content_type='application/json',
        ),
    )


@pytest.mark.asyncio
async def test_generate_json_format_unconstrained(
    setup_test: SetupFixture,
) -> None:
    """When output_schema is provided, format will default to json"""
    ai, *_ = setup_test

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        output_schema=TestSchema,
        output_constrained=False,
    )

    assert response.request == GenerateRequest(
        messages=[
            Message(role=Role.USER, content=[TextPart(text='hi')]),
        ],
        config={},
        tools=[],
        output=OutputConfig(
            format='json',
            schema_={
                'properties': {
                    'foo': {
                        'default': None,
                        'description': 'foo field',
                        'title': 'Foo',
                        'type': 'integer',
                    },
                    'bar': {
                        'default': None,
                        'description': 'bar field',
                        'title': 'Bar',
                        'type': 'string',
                    },
                },
                'title': 'TestSchema',
                'type': 'object',
            },
            constrained=False,
            content_type='application/json',
        ),
    )


@pytest.mark.asyncio
async def test_generate_json_format_unconstrained_with_instructions(
    setup_test: SetupFixture,
) -> None:
    """When output_schema is provided, format will default to json"""
    ai, *_ = setup_test

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        output_schema=TestSchema,
        output_instructions=True,
        output_constrained=False,
    )

    assert response.request == GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='hi'),
                    TextPart(
                        text='Output should be in JSON format and conform to the following schema:\n\n```\n{"properties": {"foo": {"default": null, "description": "foo field", "title": "Foo", "type": "integer"}, "bar": {"default": null, "description": "bar field", "title": "Bar", "type": "string"}}, "title": "TestSchema", "type": "object"}\n```\n',
                        metadata=Metadata(root={'purpose': 'output'}),
                    ),
                ],
            )
        ],
        config={},
        tools=[],
        output=OutputConfig(
            format='json',
            schema_={
                'properties': {
                    'foo': {
                        'default': None,
                        'description': 'foo field',
                        'title': 'Foo',
                        'type': 'integer',
                    },
                    'bar': {
                        'default': None,
                        'description': 'bar field',
                        'title': 'Bar',
                        'type': 'string',
                    },
                },
                'title': 'TestSchema',
                'type': 'object',
            },
            constrained=False,
            content_type='application/json',
        ),
    )


class TestFormat(FormatDef):
    def __init__(self):
        super().__init__(
            'banana',
            FormatterConfig(
                format='json',
                content_type='application/banana',
                constrained=True,
            ),
        )

    def handle(self, schema) -> Formatter:
        def message_parser(msg: Message):
            return f'banana {"".join(p.root.text for p in msg.content)}'

        def chunk_parser(chunk):
            return f'banana chunk {"".join(p.root.text for p in chunk.content)}'

        instructions: str | None

        if schema:
            instructions = f'schema: {json.dumps(schema)}'

        return Formatter(
            chunk_parser=chunk_parser,
            message_parser=message_parser,
            instructions=instructions,
        )


@pytest.mark.asyncio
async def test_define_format(setup_test: SetupFixture) -> None:
    ai, _, pm, *_ = setup_test

    ai.define_format(TestFormat())

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    pm.responses = [
        (
            GenerateResponse(
                finishReason=FinishReason.STOP,
                message=Message(
                    role=Role.MODEL, content=[TextPart(text='model says')]
                ),
            )
        )
    ]
    pm.chunks = [
        [
            GenerateResponseChunk(role='model', content=[TextPart(text='1')]),
            GenerateResponseChunk(role='model', content=[TextPart(text='2')]),
            GenerateResponseChunk(role='model', content=[TextPart(text='3')]),
        ]
    ]

    chunks = []

    def collect_chunks(chunk):
        chunks.append(chunk.output)

    response = await ai.generate(
        model='programmableModel',
        prompt='hi',
        output_format='banana',
        output_schema=TestSchema,
        on_chunk=collect_chunks,
    )

    assert response.output == 'banana model says'
    assert chunks == ['banana chunk 1', 'banana chunk 2', 'banana chunk 3']

    assert response.request == GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='hi'),
                    TextPart(
                        text='schema: {"properties": {"foo": {"default": null, "description": "foo field", "title": "Foo", "type": "integer"}, "bar": {"default": null, "description": "bar field", "title": "Bar", "type": "string"}}, "title": "TestSchema", "type": "object"}',
                        metadata=Metadata(root={'purpose': 'output'}),
                    ),
                ],
            ),
        ],
        config={},
        tools=[],
        output=OutputConfig(
            format='json',
            schema_={
                'properties': {
                    'foo': {
                        'default': None,
                        'description': 'foo field',
                        'title': 'Foo',
                        'type': 'integer',
                    },
                    'bar': {
                        'default': None,
                        'description': 'bar field',
                        'title': 'Bar',
                        'type': 'string',
                    },
                },
                'title': 'TestSchema',
                'type': 'object',
            },
            # these get populated by the format
            constrained=True,
            content_type='application/banana',
        ),
    )
