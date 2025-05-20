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

import base64
import sys
import unittest
from unittest.mock import ANY, AsyncMock, MagicMock, patch

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

import pytest
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from genkit.ai import ActionRunContext, Genkit
from genkit.core.action.types import ActionResponse
from genkit.core.schema import to_json_schema
from genkit.plugins.google_genai.models.gemini import (
    DEFAULT_SUPPORTS_MODEL,
    GeminiModel,
    GoogleAIGeminiVersion,
    VertexAIGeminiVersion,
    google_model_info,
)
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    MediaPart,
    Message,
    ModelInfo,
    Part,
    Role,
    TextPart,
    ToolDefinition,
)

ALL_VERSIONS = list(GoogleAIGeminiVersion) + list(VertexAIGeminiVersion)
IMAGE_GENERATION_VERSIONS = [GoogleAIGeminiVersion.GEMINI_2_0_FLASH_EXP]


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in ALL_VERSIONS])
async def test_generate_text_response(mocker, version):
    """Test the generate method for text responses."""
    response_text = 'request answer'
    request_text = 'response question'

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == response_text


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in ALL_VERSIONS])
async def test_generate_stream_text_response(mocker, version):
    """Test the generate method for text responses."""
    response_text = 'request answer'
    request_text = 'response question'

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(text=request_text),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))

    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content_stream.__aiter__.side_effect = [resp]
    on_chunk_mock = mocker.MagicMock()
    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext(on_chunk=on_chunk_mock)
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content_stream(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content == []


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in IMAGE_GENERATION_VERSIONS])
async def test_generate_media_response(mocker, version):
    """Test generate method for media responses."""
    request_text = 'response question'
    response_byte_string = b'\x89PNG\r\n\x1a\n'
    response_mimetype = 'image/png'
    modalities = ['Text', 'Image']

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ],
        config={'response_modalities': modalities},
    )

    candidate = genai.types.Candidate(
        content=genai.types.Content(
            parts=[
                genai.types.Part(inline_data=genai.types.Blob(data=response_byte_string, mime_type=response_mimetype))
            ]
        )
    )
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=genai.types.GenerateContentConfig(response_modalities=modalities),
        )
    ])
    assert isinstance(response, GenerateResponse)

    content = response.message.content[0]
    assert isinstance(content.root, MediaPart)

    assert content.root.media.content_type == response_mimetype

    decoded_url = base64.b64decode(content.root.media.url)
    assert decoded_url == response_byte_string


def test_convert_schema_property(mocker):
    """Test _convert_schema_property."""
    googleai_client_mock = mocker.AsyncMock()
    gemini = GeminiModel('abc', googleai_client_mock, mocker.MagicMock())

    class Simple(BaseModel):
        foo: str = Field(description='foo field')
        bar: int = Field(description='bar field')
        baz: list[str] = Field(default=None, description='bar field')

    assert gemini._convert_schema_property(to_json_schema(Simple)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
            ),
            'bar': genai_types.Schema(
                type='INTEGER',
                description='bar field',
            ),
            'baz': genai_types.Schema(
                type='ARRAY',
                description='bar field',
                items={'type': 'string'},
            ),
        },
        required=['foo', 'bar'],
    )

    class Nested(BaseModel):
        baz: int = Field(description='baz field')

    class WithNested(BaseModel):
        foo: str = Field(description='foo field')
        bar: Nested = Field(description='bar field')

    assert gemini._convert_schema_property(to_json_schema(WithNested)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
            ),
            'bar': genai_types.Schema(
                type='OBJECT',
                description='bar field',
                properties={
                    'baz': genai_types.Schema(
                        type='INTEGER',
                        description='baz field',
                    ),
                },
                required=['baz'],
            ),
        },
        required=['foo', 'bar'],
    )

    class TestEnum(StrEnum):
        FOO = 'foo'
        BAR = 'bar'

    class WitEnum(BaseModel):
        foo: TestEnum = Field(description='foo field')

    assert gemini._convert_schema_property(to_json_schema(WitEnum)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
                enum=['foo', 'bar'],
            ),
        },
        required=['foo'],
    )


@pytest.mark.asyncio
async def test_generate_with_system_instructions(mocker):
    """Test Generate using system instructions."""
    response_text = 'request answer'
    request_text = 'response question'
    system_instruction = 'system instruciton text'
    version = GoogleAIGeminiVersion.GEMINI_2_0_FLASH

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
            Message(
                role=Role.SYSTEM,
                content=[
                    TextPart(text=system_instruction),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    expected_system_instruction = genai.types.Content(parts=[genai.types.Part(text=system_instruction)])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())
    ctx = ActionRunContext()

    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=genai.types.GenerateContentConfig(system_instruction=expected_system_instruction),
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == response_text


# Unit tests


@pytest.mark.parametrize(
    'input, expected',
    [
        (
            'lazaro',
            ModelInfo(
                label='Google AI - lazaro',
                supports=DEFAULT_SUPPORTS_MODEL,
            ),
        ),
        (
            'gemini-4-0-pro-delux-max',
            ModelInfo(
                label='Google AI - gemini-4-0-pro-delux-max',
                supports=DEFAULT_SUPPORTS_MODEL,
            ),
        ),
    ],
)
def test_google_model_info(input, expected):
    """Tests for google_model_info."""
    model_info = google_model_info(input)

    assert model_info == expected


@pytest.fixture
def gemini_model_instance():
    """Common initialization of GeminiModel."""
    mock_registry = MagicMock(spec=Genkit)
    version = 'version'
    mock_client = MagicMock(spec=genai.Client)

    return GeminiModel(
        version=version,
        client=mock_client,
        registry=mock_registry,
    )


def test_gemini_model__init__():
    """Test for init gemini model."""
    mock_registry = MagicMock(spec=Genkit)
    version = 'version'
    mock_client = MagicMock(spec=genai.Client)

    model = GeminiModel(
        version=version,
        client=mock_client,
        registry=mock_registry,
    )

    assert isinstance(model, GeminiModel)
    assert model._version == version
    assert model._client == mock_client
    assert model._registry == mock_registry


@patch('genkit.plugins.google_genai.models.gemini.GeminiModel._create_tool')
def test_gemini_model__get_tools(
    mock_create_tool,
    gemini_model_instance,
):
    """Unit test for GeminiModel._get_tools."""
    mock_create_tool.return_value = genai_types.Tool()

    request_tools = [
        ToolDefinition(
            name='tool_1',
            description='model tool description',
            input_schema={},
            outputSchema={
                'type': 'object',
                'properties': {
                    'test': {'type': 'string', 'description': 'test field'},
                },
            },
            metadata={'date': 'today'},
        ),
        ToolDefinition(
            name='tool_2',
            description='model tool description',
            input_schema={},
            outputSchema={
                'type': 'object',
                'properties': {
                    'test': {'type': 'string', 'description': 'test field'},
                },
            },
            metadata={'date': 'today'},
        ),
    ]

    request = GenerateRequest(
        tools=request_tools,
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='test text'),
                ],
            ),
        ],
    )

    tools = gemini_model_instance._get_tools(request)

    assert len(tools) == len(request_tools)
    for tool in tools:
        assert isinstance(tool, genai_types.Tool)


@patch('genkit.plugins.google_genai.models.gemini.GeminiModel._convert_schema_property')
def test_gemini_model__create_tool(mock_convert_schema_property, gemini_model_instance):
    """Unit tests for GeminiModel._create_tool."""
    tool_defined = ToolDefinition(
        name='model_tool',
        description='model tool description',
        input_schema={
            'type': 'str',
            'description': 'test field',
        },
        outputSchema={
            'type': 'object',
            'properties': {
                'test': {'type': 'string', 'description': 'test field'},
            },
        },
        metadata={'date': 'today'},
    )

    mock_convert_schema_property.return_value = genai_types.Schema()

    gemini_tool = gemini_model_instance._create_tool(
        tool_defined,
    )

    assert isinstance(gemini_tool, genai_types.Tool)


@pytest.mark.parametrize(
    'input_schema, defs, expected_schema',
    [
        # Test Case 1: None input_schema
        (
            None,
            None,
            None,
        ),
        # Test Case 2: input_schema without 'type'
        (
            {'description': 'A simple description'},
            None,
            None,
        ),
        # Test Case 3: Simple string type
        (
            {'type': 'STRING', 'description': 'A string field', 'required': ['field']},
            None,
            genai_types.Schema(description='A string field', required=['field'], type=genai_types.Type.STRING),
        ),
        # Test Case 4: String with enum
        (
            {'type': 'STRING', 'enum': ['A', 'B']},
            None,
            genai_types.Schema(type=genai_types.Type.STRING, enum=['A', 'B']),
        ),
        # Test Case 5: Array of strings
        (
            {'type': genai_types.Type.ARRAY, 'items': {'type': 'STRING'}},
            None,
            genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(type=genai_types.Type.STRING),
            ),
        ),
        # Test Case 6: Empty object
        (
            {'type': 'OBJECT', 'properties': {}},
            None,
            genai_types.Schema(type=genai_types.Type.OBJECT, properties={}),
        ),
        # Test Case 7: Object with simple properties
        (
            {
                'type': 'OBJECT',
                'properties': {
                    'prop1': {'type': 'STRING'},
                    'prop2': {'type': 'NUMBER', 'description': 'Numeric field'},
                },
            },
            None,
            genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    'prop1': genai_types.Schema(type=genai_types.Type.STRING),
                    'prop2': genai_types.Schema(type=genai_types.Type.NUMBER, description='Numeric field'),
                },
            ),
        ),
        # Test Case 8: Object with nested $ref
        (
            {
                'type': 'OBJECT',
                'properties': {'user': {'$ref': '#/$defs/User'}},
                '$defs': {'User': {'type': 'OBJECT', 'properties': {'name': {'type': 'STRING'}}}},
            },
            None,  # defs will be picked from input_schema['$defs']
            genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    'user': genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={'name': genai_types.Schema(type=genai_types.Type.STRING)},
                    )
                },
            ),
        ),
        # Test Case 9: Object with nested $ref and existing defs
        (
            {
                'type': 'OBJECT',
                'properties': {'address': {'$ref': '#/$defs/Address'}},
            },
            {'Address': {'type': 'OBJECT', 'properties': {'street': {'type': 'STRING'}}}},
            genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    'address': genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={'street': genai_types.Schema(type=genai_types.Type.STRING)},
                    )
                },
            ),
        ),
        # Test Case 10: Object with $ref and description at the $ref level
        (
            {
                'type': 'OBJECT',
                'properties': {
                    'item': {
                        '$ref': '#/$defs/Item',
                        'description': 'A referenced item description',
                    }
                },
                '$defs': {'Item': {'type': 'STRING'}},
            },
            None,
            genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    'item': genai_types.Schema(
                        type=genai_types.Type.STRING, description='A referenced item description'
                    )
                },
            ),
        ),
    ],
)
def test_gemini_model__convert_schema_property(
    input_schema,
    defs,
    expected_schema,
    gemini_model_instance,
):
    """Unit tests for  GeminiModel._convert_schema_property with various valid schema inputs."""
    result_schema = gemini_model_instance._convert_schema_property(input_schema, defs)

    if expected_schema is None:
        assert result_schema is None
    else:

        def compare_schemas(s1: genai_types.Schema, s2: genai_types.Schema):
            assert s1.description == s2.description
            assert s1.required == s2.required
            assert s1.type == s2.type
            assert s1.enum == s2.enum

            if s1.items or s2.items:
                assert s1.items is not None and s2.items is not None
                compare_schemas(s1.items, s2.items)
            else:
                assert s1.items is None and s2.items is None

            if s1.properties or s2.properties:
                assert s1.properties is not None and s2.properties is not None
                assert set(s1.properties.keys()) == set(s2.properties.keys())
                for key in s1.properties:
                    compare_schemas(s1.properties[key], s2.properties[key])
            else:
                assert (s1.properties is None and s2.properties is None) or (
                    len(s1.properties) == 0 and len(s2.properties) == 0
                )

        compare_schemas(result_schema, expected_schema)


@pytest.mark.parametrize(
    'input_schema, defs',
    [
        # Test Case 11: Unresolvable $ref
        (
            {'type': 'OBJECT', 'properties': {'user': {'$ref': '#/$defs/NonExistent'}}},
            {'$defs': {'SomeOtherDef': {'type': 'STRING'}}},
        ),
        # Test Case 12: $ref with missing defs dict
        (
            {'type': 'OBJECT', 'properties': {'user': {'$ref': '#/$defs/NonExistent'}}},
            None,
        ),
    ],
)
def test_gemini_model__convert_schema_property_raises_exception(input_schema, defs, gemini_model_instance):
    """Test GeminiModel._convert_schema_property raises an exception for unresolvable schemas."""
    with pytest.raises(ValueError, match=r'Failed to resolve schema for .*'):
        gemini_model_instance._convert_schema_property(input_schema, defs)


@pytest.mark.parametrize(
    'tool_name, tool_response',
    [
        ('tool-1', 'tool 1 response'),
        ('tool-2', {'complex_response': True}),
    ],
)
def test_gemini_model__call_tool(
    tool_name,
    tool_response,
    gemini_model_instance,
):
    """Unit tests for GeminiModel._call_tool."""
    mock_tool = MagicMock()
    mock_tool.input_type.validate_python.return_value = []
    mock_tool.run.return_value = ActionResponse(response=tool_response, trace_id='trace-id')

    gemini_model_instance._registry = MagicMock()
    gemini_model_instance._registry.registry.lookup_action.return_value = mock_tool

    call = genai_types.FunctionCall(name=tool_name)
    response = gemini_model_instance._call_tool(call)

    assert isinstance(response, genai_types.Content)
    assert response.parts[0].function_response.name == tool_name
    assert response.parts[0].function_response.response == {'content': tool_response}


def test_gemini_model__call_tool_raises_exception(gemini_model_instance):
    """Unit tests for GeminiModel._call_tool function not found."""
    gemini_model_instance._registry = MagicMock()
    gemini_model_instance._registry.registry.lookup_action.return_value = None

    with pytest.raises(LookupError, match=r'Tool .* not found'):
        gemini_model_instance._call_tool(genai_types.FunctionCall(name='tool_name'))


@pytest.mark.asyncio
@patch(
    'genkit.plugins.google_genai.models.context_caching.utils.generate_cache_key',
    new_callable=MagicMock,
)
@patch(
    'genkit.plugins.google_genai.models.context_caching.utils.validate_context_cache_request',
    new_callable=MagicMock,
)
@pytest.mark.parametrize(
    'cache_key',
    [
        'key_not_cached',
        'key1',
    ],
)
async def test_gemini_model__retrieve_cached_content(
    mock_generate_cache_key,
    mock_validate_context_cache_request,
    cache_key,
    gemini_model_instance,
):
    """Unit tests for GeminiModel._retrieve_cached_content."""
    # Mock cache utils
    mock_generate_cache_key.return_value = cache_key
    mock_validate_context_cache_request.return_value = None

    # Mock pager object
    class MockPage(AsyncMock):
        display_name: str

    async_mock_list = AsyncMock()
    mock_client = MagicMock()
    mock_client.aio.caches.list = async_mock_list

    async_mock_list.__aiter__.return_value = [MockPage(display_name='key1'), MockPage(display_name='key2')]

    # Mock update and create cache methods of google genai
    async_cache = AsyncMock()
    async_cache.return_value = genai_types.CachedContent()
    mock_client.aio.caches.update = async_cache
    mock_client.aio.caches.create = async_cache

    gemini_model_instance._client = mock_client

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='request text'),
                ],
            ),
        ]
    )

    cache = await gemini_model_instance._retrieve_cached_content(
        request=request,
        model_name='gemini-1.5-flash-001',
        cache_config={},
        contents=[],
    )

    assert isinstance(cache, genai_types.CachedContent)
