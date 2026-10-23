# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0

"""Tests driving a Genkit-backed MCP server through an in-memory client."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from genkit_mcp._server import McpServer, create_mcp_server
from mcp import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult, ImageContent, TextContent
from pydantic import BaseModel
from structlog.testing import capture_logs

from genkit import Genkit, GenkitError, MultipartToolResponse, Part, ToolRunContext, tool as genkit_tool
from genkit.plugin_api import Action


class Shelf(BaseModel):
    """Output of a tool whose schema MCP can advertise."""

    title: str
    count: int


class Greeting(BaseModel):
    """Input of a tool whose schema MCP can carry."""

    name: str


@asynccontextmanager
async def connected(server: McpServer) -> AsyncIterator[ClientSession]:
    """Drive a server over the SDK's in-memory transport."""
    async with create_connected_server_and_client_session(server._server, raise_exceptions=True) as session:
        yield session


def app() -> Genkit:
    return Genkit()


def text_of(result: CallToolResult) -> str:
    """Join the text blocks of a result, ignoring any other block kind."""
    return ''.join(block.text for block in result.content if isinstance(block, TextContent))


@pytest.mark.asyncio
async def test_a_tool_defined_after_the_server_is_still_listed() -> None:
    """Listing reads the app per request, so late definitions are not missed."""
    ai = app()
    server = create_mcp_server(ai, 'bookshop')

    @ai.tool()
    async def late() -> str:
        """Defined after the server was built."""
        return 'here'

    async with connected(server) as session:
        listed = await session.list_tools()

    assert [tool.name for tool in listed.tools] == ['late']
    assert listed.tools[0].description == 'Defined after the server was built.'


@pytest.mark.asyncio
async def test_the_server_advertises_its_name_and_version() -> None:
    ai = app()
    server = create_mcp_server(ai, 'bookshop', version='2.1.0')

    async with connected(server) as session:
        result = await session.initialize()

    assert result.serverInfo.name == 'bookshop'
    assert result.serverInfo.version == '2.1.0'


@pytest.mark.asyncio
async def test_capabilities_offer_tools_and_nothing_else() -> None:
    """Prompts and resources are not served, so they are not advertised."""
    ai = app()
    server = create_mcp_server(ai, 'bookshop')

    async with connected(server) as session:
        result = await session.initialize()

    assert result.capabilities.tools is not None
    assert result.capabilities.prompts is None
    assert result.capabilities.resources is None


@pytest.mark.asyncio
async def test_a_string_tool_returns_text() -> None:
    ai = app()

    @ai.tool()
    async def greet(greeting: Greeting) -> str:
        """Greet."""
        return f'hello {greeting.name}'

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        result = await session.call_tool('greet', {'name': 'ada'})

    assert result.content == [TextContent(type='text', text='hello ada')]
    assert result.isError is False


@pytest.mark.asyncio
async def test_a_tool_with_a_scalar_argument_is_neither_listed_nor_callable() -> None:
    """MCP arguments are an object, so such a tool cannot be described or invoked."""
    ai = app()

    @ai.tool()
    async def shout(word: str) -> str:
        """Shout."""
        return word.upper()

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        listed = await session.list_tools()
        result = await session.call_tool('shout', {'word': 'hi'})

    assert listed.tools == []
    assert result.isError is True
    assert 'is not registered' in text_of(result)


@pytest.mark.asyncio
async def test_an_object_tool_returns_structured_content_and_advertises_its_schema() -> None:
    ai = app()

    @ai.tool()
    async def shelf() -> Shelf:
        """Describe a shelf."""
        return Shelf(title='Fiction', count=2)

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        listed = await session.list_tools()
        result = await session.call_tool('shelf', {})

    assert listed.tools[0].outputSchema is not None
    assert listed.tools[0].outputSchema.get('type') == 'object'
    assert result.structuredContent == {'title': 'Fiction', 'count': 2}


@pytest.mark.asyncio
async def test_a_media_tool_returns_image_content() -> None:
    ai = app()

    @ai.tool()
    async def cover() -> MultipartToolResponse:
        """Return a cover image."""
        return MultipartToolResponse(
            output=None,
            content=[Part.from_media(url='data:image/png;base64,aW1n', content_type='image/png')],
        )

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        result = await session.call_tool('cover', {})

    assert result.content == [ImageContent(type='image', mimeType='image/png', data='aW1n')]


@pytest.mark.asyncio
async def test_a_raising_tool_becomes_an_error_result_carrying_its_message() -> None:
    ai = app()

    @ai.tool()
    async def explode() -> str:
        """Fail."""
        raise ValueError('shelf collapsed')

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        result = await session.call_tool('explode', {})

    assert result.isError is True
    assert result.content == [TextContent(type='text', text="Tool 'explode' failed")]


@pytest.mark.asyncio
async def test_a_genkit_error_keeps_its_status_and_message_but_not_its_cause() -> None:
    """A GenkitError's message is the app's choice, and its cause's text is not."""
    ai = app()

    @ai.tool()
    async def book() -> str:
        """Fail on purpose."""
        raise GenkitError(
            status='INVALID_ARGUMENT',
            message='date must be in the future',
            cause=RuntimeError('GET https://api.example.com/v1?key=SECRET failed'),
        )

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        result = await session.call_tool('book', {})

    assert result.isError is True
    assert result.content == [TextContent(type='text', text='INVALID_ARGUMENT: date must be in the future')]


@pytest.mark.asyncio
async def test_the_request_meta_reaches_the_tool_context() -> None:
    ai = app()
    seen: list[object] = []

    @ai.tool()
    async def trace(ctx: ToolRunContext) -> str:
        """Record the context."""
        seen.append(ctx.context)
        return 'ok'

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        await session.call_tool('trace', {}, meta={'requestId': 'r-1'})

    assert seen == [{'mcp': {'_meta': {'requestId': 'r-1'}}}]


@pytest.mark.asyncio
async def test_a_tool_mcp_cannot_describe_is_warned_about_once() -> None:
    """Listing and calling reuse each description, so the warning does not repeat per request."""
    ai = app()

    @ai.tool()
    async def shout(word: str) -> str:
        """Shout."""
        return word.upper()

    @ai.tool()
    async def ping() -> str:
        """Answer."""
        return 'pong'

    with capture_logs() as logs:
        async with connected(create_mcp_server(ai, 'bookshop')) as session:
            await session.list_tools()
            await session.call_tool('ping', {})
            await session.list_tools()

    assert [entry['event'] for entry in logs if entry['log_level'] == 'warning'] == [
        'skipping a tool whose input is not an object, which MCP arguments cannot express'
    ]


@pytest.mark.asyncio
async def test_an_unknown_tool_is_an_error_result() -> None:
    ai = app()

    @ai.tool()
    async def known() -> str:
        """Exist."""
        return 'here'

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        result = await session.call_tool('missing', {})

    assert result.isError is True
    assert 'is not registered' in text_of(result)


@pytest.mark.asyncio
async def test_tools_a_dynamic_action_provider_serves_are_not_served() -> None:
    """Only tools defined on the app are served, as in JS and Go."""
    ai = app()

    @ai.tool()
    async def known() -> str:
        """Exist."""
        return 'here'

    async def remote() -> str:
        """Served by a provider."""
        return 'there'

    async def provide() -> dict[str, list[Action]]:
        return {'tool': [genkit_tool(remote, name='remote').action()]}

    ai.define_dynamic_action_provider('elsewhere', provide)

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        listed = await session.list_tools()
        result = await session.call_tool('remote', {})

    assert [tool.name for tool in listed.tools] == ['known']
    assert result.isError is True


@pytest.mark.asyncio
async def test_a_no_arg_tool_advertises_an_object_input_schema() -> None:
    ai = app()

    @ai.tool()
    async def ping() -> str:
        """Answer."""
        return 'pong'

    async with connected(create_mcp_server(ai, 'bookshop')) as session:
        listed = await session.list_tools()

    assert listed.tools[0].inputSchema == {'type': 'object', 'properties': {}}
