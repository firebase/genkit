#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pytest
from genkit.ai.testing_utils import define_echo_model, define_programmable_model
from genkit.core.typing import (
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    Message,
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


@pytest.fixture
def setup_test():
    ai = Genkit(model='echoModel')

    pm, _ = define_programmable_model(ai)
    echo, _ = define_echo_model(ai)

    return (ai, echo, pm)


@pytest.mark.asyncio
async def test_generate_uses_default_model(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(prompt='hi', config={'temperature': 11})

    assert response.text() == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_explicit_model(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        model='echoModel', prompt='hi', config={'temperature': 11}
    )

    assert response.text() == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_str_prompt(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(prompt='hi', config={'temperature': 11})

    assert response.text() == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_part_prompt(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        prompt=TextPart(text='hi'), config={'temperature': 11}
    )

    assert response.text() == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_part_list_prompt(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        prompt=[TextPart(text='hello'), TextPart(text='world')],
        config={'temperature': 11},
    )

    assert response.text() == '[ECHO] user: "hello","world" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_str_system(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system='talk like pirate', prompt='hi', config={'temperature': 11}
    )

    assert (
        response.text()
        == '[ECHO] system: "talk like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_part_system(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system=TextPart(text='talk like pirate'),
        prompt='hi',
        config={'temperature': 11},
    )

    assert (
        response.text()
        == '[ECHO] system: "talk like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_part_list_system(setup_test) -> None:
    ai, *_ = setup_test

    response = await ai.generate(
        system=[TextPart(text='talk'), TextPart(text='like pirate')],
        prompt='hi',
        config={'temperature': 11},
    )

    assert (
        response.text()
        == '[ECHO] system: "talk","like pirate" user: "hi" {"temperature": 11}'
    )


@pytest.mark.asyncio
async def test_generate_with_messages(setup_test) -> None:
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

    assert response.text() == '[ECHO] user: "hi" {"temperature": 11}'


@pytest.mark.asyncio
async def test_generate_with_system_prompt_messages(setup_test) -> None:
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
        response.text()
        == '[ECHO] system: "talk like pirate" user: "hi" model: "bye" user: "hi again"'
    )


@pytest.mark.asyncio
async def test_generate_with_tools(setup_test) -> None:
    ai, echo, *_ = setup_test

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        tool_choice='required',
        tools=['testTool'],
    )

    assert response.text() == '[ECHO] user: "hi" tool_choice=required'
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
async def test_generate_with_tools(setup_test) -> None:
    ai, _, pm, *_ = setup_test

    class ToolInput(BaseModel):
        value: int = Field(None, description='value field')

    @ai.tool('the tool', name='testTool')
    def test_tool(input: ToolInput):
        return 'abc'

    tool_request_msg = Message(
        role=Role.MODEL,
        content=[
            ToolRequestPart(
                toolRequest=ToolRequest1(
                    input={'value': 5}, name='testTool', ref='123'
                )
            )
        ],
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

    assert response.text() == 'tool called'
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
async def test_generate_with_output(setup_test) -> None:
    ai, *_ = setup_test

    class TestSChema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    response = await ai.generate(
        model='echoModel',
        prompt='hi',
        constrained=True,
        output_format='json',
        content_type='application/json',
        output_schema=TestSChema,
        output_instructions=True,
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
                'title': 'TestSChema',
                'type': 'object',
            },
            constrained=True,
            content_type='application/json',
        ),
    )
