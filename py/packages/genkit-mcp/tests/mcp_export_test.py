# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for translating Genkit tools and results into MCP shapes."""

from typing import Any

import pytest
from genkit_mcp._export import error_result, multipart_to_call_result, tool_to_mcp
from mcp.types import (
    AudioContent,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
)
from pydantic import AnyUrl, BaseModel
from structlog.testing import capture_logs

from genkit import Genkit, MultipartToolResponse, Part
from genkit._core._typing import Resource


def media(url: str, content_type: str | None = None) -> Part:
    return Part.from_media(url=url, content_type=content_type)


@pytest.mark.parametrize(
    ('output', 'text', 'structured'),
    [
        ('plain text', 'plain text', None),
        ({'a': 1}, '{"a": 1}', {'a': 1}),
        ([1, 'x'], '[1, "x"]', None),
        (42, '42', None),
        (True, 'true', None),
        (None, None, None),
    ],
)
def test_output_travels_as_text_and_only_a_dict_is_structured(
    output: object, text: str | None, structured: dict[str, Any] | None
) -> None:
    """Only an object can be structuredContent, so everything else is JSON text."""
    result = multipart_to_call_result(MultipartToolResponse(output=output), 'tool')

    assert [block.text for block in result.content if isinstance(block, TextContent)] == ([text] if text else [])
    assert result.structuredContent == structured
    assert result.isError in (False, None)


def test_an_image_data_url_becomes_image_content() -> None:
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[media('data:image/png;base64,aW1n', 'image/png')]),
        'tool',
    )

    assert result.content == [ImageContent(type='image', mimeType='image/png', data='aW1n')]


def test_an_audio_data_url_becomes_audio_content() -> None:
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[media('data:audio/mpeg;base64,c25k', 'audio/mpeg')]),
        'tool',
    )

    assert result.content == [AudioContent(type='audio', mimeType='audio/mpeg', data='c25k')]


def test_other_binary_content_becomes_an_embedded_resource_with_a_minted_uri() -> None:
    """BlobResourceContents requires a uri, and Genkit media carries none."""
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[media('data:application/pdf;base64,cGRm', 'application/pdf')]),
        'bookshop',
    )

    block = result.content[0]
    assert isinstance(block, EmbeddedResource)
    assert str(block.resource.uri) == 'genkit://tool/bookshop/content/0'
    assert block.resource.mimeType == 'application/pdf'


def test_a_non_data_media_url_becomes_a_resource_link() -> None:
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[media('https://example.test/a.png', 'image/png')]),
        'tool',
    )

    assert result.content == [
        ResourceLink(
            type='resource_link',
            uri=AnyUrl('https://example.test/a.png'),
            name='https://example.test/a.png',
            mimeType='image/png',
        )
    ]


def test_a_resource_part_becomes_a_resource_link() -> None:
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[Part(resource=Resource(uri='https://example.test/docs'))]),
        'tool',
    )

    assert result.content == [
        ResourceLink(type='resource_link', uri=AnyUrl('https://example.test/docs'), name='https://example.test/docs')
    ]


def test_a_text_part_follows_an_object_output() -> None:
    """Clients read an object back from structuredContent, so the text part cannot change it."""
    result = multipart_to_call_result(
        MultipartToolResponse(output={'a': 1}, content=[Part(text='note')]),
        'tool',
    )

    assert [block.text for block in result.content if isinstance(block, TextContent)] == ['{"a": 1}', 'note']


@pytest.mark.parametrize('output', ['first', [1, 2], 42])
def test_a_text_part_beside_a_non_object_output_is_dropped_with_a_warning(output: object) -> None:
    """Clients join text blocks into the output, so sending the part would change it."""
    with capture_logs() as logs:
        result = multipart_to_call_result(MultipartToolResponse(output=output, content=[Part(text='note')]), 'tool')

    assert len(result.content) == 1
    assert [entry['log_level'] for entry in logs] == ['warning']


def test_text_parts_without_output_are_sent_in_order() -> None:
    result = multipart_to_call_result(
        MultipartToolResponse(output=None, content=[Part(text='first'), Part(text='second')]),
        'tool',
    )

    assert [block.text for block in result.content if isinstance(block, TextContent)] == ['first', 'second']


@pytest.mark.parametrize('url', ['/covers/a.png', 'covers/a.png'])
def test_a_media_part_with_a_relative_url_is_dropped_with_a_warning(url: str) -> None:
    """A resource link needs an absolute URI, and one bad part must not fail a call that succeeded."""
    with capture_logs() as logs:
        result = multipart_to_call_result(
            MultipartToolResponse(output='ok', content=[media(url, 'image/png')]),
            'tool',
        )

    assert result.content == [TextContent(type='text', text='ok')]
    assert [entry['log_level'] for entry in logs] == ['warning']


def test_a_part_mcp_cannot_carry_is_dropped_with_a_warning() -> None:
    with capture_logs() as logs:
        result = multipart_to_call_result(
            MultipartToolResponse(output=None, content=[Part(reasoning='thinking')]),
            'tool',
        )

    assert result.content == []
    assert [entry['log_level'] for entry in logs] == ['warning']


def test_metadata_travels_as_meta() -> None:
    result = multipart_to_call_result(MultipartToolResponse(output='x', metadata={'trace': 'a'}), 'tool')

    assert result.meta == {'trace': 'a'}


def test_a_re_exported_error_stays_an_error_without_accreting_the_flag() -> None:
    """A client error envelope came from an MCP error, and goes back out as one."""
    response: MultipartToolResponse[object] = MultipartToolResponse(
        output={'error': 'upstream failed'},
        metadata={'trace': 'a', 'isError': True},
    )

    result = multipart_to_call_result(response, 'tool')

    assert result.isError is True
    assert result.content == [TextContent(type='text', text='upstream failed')]
    assert result.meta == {'trace': 'a'}


def test_error_result_carries_only_the_message() -> None:
    result = error_result('Tool "missing" is not registered')

    assert result.isError is True
    assert result.content == [TextContent(type='text', text='Tool "missing" is not registered')]
    assert result.meta is None


@pytest.mark.asyncio
async def test_a_no_arg_tool_advertises_an_object_schema() -> None:
    """Core infers {} for a no-arg tool, which MCP arguments cannot express."""
    ai = Genkit()

    @ai.tool()
    async def ping() -> str:
        """Answer."""
        return 'pong'

    tool = tool_to_mcp(ping.action())

    assert tool is not None
    assert tool.inputSchema == {'type': 'object', 'properties': {}}
    assert tool.description == 'Answer.'


@pytest.mark.asyncio
async def test_a_tool_with_a_scalar_argument_is_skipped_with_a_warning() -> None:
    """MCP arguments are always an object, so a scalar-input tool cannot be listed."""
    ai = Genkit()

    @ai.tool()
    async def shout(word: str) -> str:
        """Shout."""
        return word.upper()

    action = shout.action()
    action.input_schema = {'type': 'string'}

    with capture_logs() as logs:
        tool = tool_to_mcp(action)

    assert tool is None
    assert [entry['log_level'] for entry in logs] == ['warning']


class Node(BaseModel):
    """A model that refers to itself, which pydantic describes with a top-level $ref."""

    label: str
    children: list['Node'] = []


@pytest.mark.asyncio
async def test_a_tool_whose_input_refers_to_itself_is_described_as_an_object() -> None:
    ai = Genkit()

    @ai.tool()
    async def tree(node: Node) -> int:
        """Count nodes."""
        return 1 + len(node.children)

    tool = tool_to_mcp(tree.action())

    assert tool is not None
    assert tool.inputSchema['type'] == 'object'
    assert tool.inputSchema['properties']['children']['items'] == {'$ref': '#/$defs/Node'}
    assert 'Node' in tool.inputSchema['$defs']
    assert '$ref' not in tool.inputSchema


@pytest.mark.asyncio
async def test_a_schema_with_properties_but_no_type_is_described_as_an_object() -> None:
    ai = Genkit()

    @ai.tool()
    async def greet(name: str) -> str:
        """Greet."""
        return name

    action = greet.action()
    action.input_schema = {'properties': {'name': {'type': 'string'}}, 'required': ['name']}

    tool = tool_to_mcp(action)

    assert tool is not None
    assert tool.inputSchema == {'type': 'object', 'properties': {'name': {'type': 'string'}}, 'required': ['name']}


@pytest.mark.asyncio
async def test_an_optional_object_input_is_skipped_with_a_warning() -> None:
    """``Optional[Model]`` is ``anyOf`` with null, and MCP arguments are never null."""
    ai = Genkit()

    @ai.tool()
    async def maybe(node: Node | None) -> int:
        """Maybe count."""
        return 0

    with capture_logs() as logs:
        tool = tool_to_mcp(maybe.action())

    assert tool is None
    assert [entry['log_level'] for entry in logs] == ['warning']
