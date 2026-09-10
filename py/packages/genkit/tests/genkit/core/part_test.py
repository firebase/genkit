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

"""Unit tests for Part factory methods and property getters."""

import pytest
from pydantic import ValidationError

from genkit import Document, Message, Part, ToolRequest, ToolResponse
from genkit._core._typing import Media, MediaPart, PartData, ReasoningPart, TextPart

_GETTERS = ('text', 'media', 'tool_request', 'tool_response', 'data', 'reasoning', 'custom')


def assert_inactive(part: Part, *, active: str) -> None:
    for name in _GETTERS:
        if name != active:
            assert getattr(part, name) is None


def test_part_from_text() -> None:
    """Part.from_text creates a text part with direct property access."""
    p = Part.from_text('hello world', metadata={'source': 'user'})
    assert isinstance(p.root, TextPart)
    assert p.text == 'hello world'
    assert p.metadata == {'source': 'user'}
    assert_inactive(p, active='text')


def test_part_from_text_defaults() -> None:
    """from_text with no metadata leaves metadata unset."""
    p = Part.from_text('hi')
    assert p.text == 'hi'
    assert p.metadata is None


def test_part_from_text_empty() -> None:
    """Empty text is still a text part."""
    p = Part.from_text('')
    assert p.text == ''
    assert_inactive(p, active='text')


def test_part_from_media() -> None:
    """Part.from_media creates a media part with direct property access."""
    p = Part.from_media('https://example.com/image.png', content_type='image/png', metadata={'alt': 'dish'})
    assert isinstance(p.root, MediaPart)
    assert p.media is not None
    assert p.media.url == 'https://example.com/image.png'
    assert p.media.content_type == 'image/png'
    assert p.metadata == {'alt': 'dish'}
    assert_inactive(p, active='media')


def test_part_from_media_without_content_type() -> None:
    """content_type is optional."""
    p = Part.from_media('https://example.com/image.png')
    assert p.media is not None
    assert p.media.url == 'https://example.com/image.png'
    assert p.media.content_type is None
    assert p.metadata is None


def test_part_from_tool_request() -> None:
    """Part.from_tool_request creates a tool request part."""
    p = Part.from_tool_request(name='get_weather', input={'city': 'Paris'}, ref='call-123', metadata={'src': 'model'})
    assert p.tool_request is not None
    assert p.tool_request.name == 'get_weather'
    assert p.tool_request.input == {'city': 'Paris'}
    assert p.tool_request.ref == 'call-123'
    assert p.metadata == {'src': 'model'}
    assert_inactive(p, active='tool_request')


def test_part_from_tool_request_defaults() -> None:
    """name-only tool request leaves input and ref unset."""
    p = Part.from_tool_request(name='lookup')
    assert p.tool_request is not None
    assert p.tool_request.name == 'lookup'
    assert p.tool_request.input is None
    assert p.tool_request.ref is None
    assert p.metadata is None


def test_part_from_tool_response() -> None:
    """Part.from_tool_response creates a tool response part."""
    p = Part.from_tool_response(name='get_weather', output={'temp': 22}, ref='call-123')
    assert p.tool_response is not None
    assert p.tool_response.name == 'get_weather'
    assert p.tool_response.output == {'temp': 22}
    assert p.tool_response.ref == 'call-123'
    assert_inactive(p, active='tool_response')


def test_part_from_tool_response_defaults() -> None:
    """name-only tool response leaves output and ref unset."""
    p = Part.from_tool_response(name='lookup')
    assert p.tool_response is not None
    assert p.tool_response.name == 'lookup'
    assert p.tool_response.output is None
    assert p.tool_response.ref is None


def test_part_from_reasoning() -> None:
    """Part.from_reasoning creates a reasoning part."""
    p = Part.from_reasoning('thinking step by step', metadata={'step': 1})
    assert p.reasoning == 'thinking step by step'
    assert p.metadata == {'step': 1}
    assert_inactive(p, active='reasoning')


def test_part_from_data() -> None:
    """Part.from_data creates a data part."""
    p = Part.from_data({'custom': 'payload'})
    assert p.data == {'custom': 'payload'}
    assert_inactive(p, active='data')


def test_part_from_data_string() -> None:
    """data can be a string."""
    p = Part.from_data('just a string')
    assert p.data == 'just a string'


def test_part_from_data_list() -> None:
    """data can be a list."""
    p = Part.from_data([1, 2])
    assert p.data == [1, 2]


def test_part_from_custom() -> None:
    """Part.from_custom creates a custom part."""
    p = Part.from_custom({'vendor_field': True})
    assert p.custom == {'vendor_field': True}
    assert_inactive(p, active='custom')


def test_part_from_custom_empty() -> None:
    """Empty custom payload is still a custom part."""
    p = Part.from_custom({})
    assert p.custom == {}


def test_part_text_kwarg_reads_text() -> None:
    p = Part(text='hi', metadata={'source': 'user'})
    assert p.text == 'hi'
    assert p.metadata == {'source': 'user'}
    assert_inactive(p, active='text')


def test_part_media_kwarg_reads_media() -> None:
    p = Part(media=Media(url='https://x', content_type='image/png'))
    assert p.media is not None
    assert p.media.url == 'https://x'
    assert p.media.content_type == 'image/png'
    assert_inactive(p, active='media')


def test_part_tool_request_kwarg_reads_tool_request() -> None:
    p = Part(tool_request=ToolRequest(name='lookup'))
    assert p.tool_request is not None
    assert p.tool_request.name == 'lookup'
    assert_inactive(p, active='tool_request')


def test_part_tool_response_kwarg_reads_tool_response() -> None:
    p = Part(tool_response=ToolResponse(name='lookup', output={'ok': True}))
    assert p.tool_response is not None
    assert p.tool_response.name == 'lookup'
    assert p.tool_response.output == {'ok': True}
    assert_inactive(p, active='tool_response')


def test_part_data_kwarg_reads_data() -> None:
    p = Part(data={'recipe': 1})
    assert p.data == {'recipe': 1}
    assert_inactive(p, active='data')


def test_part_custom_kwarg_reads_custom() -> None:
    p = Part(custom={'vendor': True})
    assert p.custom == {'vendor': True}
    assert_inactive(p, active='custom')


def test_part_reasoning_kwarg_reads_reasoning() -> None:
    p = Part(reasoning='think')
    assert p.reasoning == 'think'
    assert_inactive(p, active='reasoning')


def test_part_text_kwarg_keeps_vendor_custom() -> None:
    p = Part(text='hi', custom={'vendor': True})
    assert p.text == 'hi'
    assert p.custom == {'vendor': True}
    assert p.data is None
    assert p.media is None


def test_part_text_and_data_kwargs_raise() -> None:
    with pytest.raises(ValidationError, match='exactly one'):
        Part(text='hi', data={'recipe': 1})


def test_kind_classes_are_not_on_genkit() -> None:
    import genkit

    assert hasattr(genkit, 'Part')
    assert hasattr(genkit, 'ToolRequest')
    assert hasattr(genkit, 'ToolResponse')
    for name in (
        'TextPart',
        'MediaPart',
        'ToolRequestPart',
        'ToolResponsePart',
        'CustomPart',
        'ReasoningPart',
    ):
        assert not hasattr(genkit, name)


def test_part_from_text_round_trip() -> None:
    """Dumping and re-parsing a factory-built part keeps the payload."""
    p = Part.from_text('hello', metadata={'source': 'user'})
    again = Part.model_validate(p.model_dump())
    assert again.text == 'hello'
    assert again.metadata == {'source': 'user'}
    assert_inactive(again, active='text')


def test_message_empty_part_raises() -> None:
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[{}])


def test_message_text_and_media_on_one_part_raises() -> None:
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[{'text': 'hi', 'media': {'url': 'https://x'}}])


def test_message_text_part_keeps_vendor_custom() -> None:
    """custom may ride on a text part."""
    msg = Message(role='user', content=[{'text': 'hi', 'custom': {'vendor': True}}])
    assert msg.content[0].text == 'hi'
    assert msg.content[0].custom == {'vendor': True}
    assert msg.content[0].media is None
    assert msg.content[0].data is None


def test_reasoning_part_keeps_signed_thought() -> None:
    """A reasoning part may carry the vendor thought blob in custom."""
    thought = {'type': 'thought', 'signature': 'sig-img', 'summary': [{'type': 'text', 'text': 'see this'}]}
    p = Part(
        root=ReasoningPart(
            reasoning='see this',
            metadata={'thoughtSignature': 'sig-img'},
            custom={'thought': thought},
        )
    )
    assert p.reasoning == 'see this'
    assert p.custom == {'thought': thought}
    assert p.metadata == {'thoughtSignature': 'sig-img'}
    assert p.text is None
    assert p.data is None


def test_message_text_and_data_on_one_part_raises() -> None:
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[{'text': 'hi', 'data': {'payload': 1}}])


def test_message_text_part_from_factory_still_works() -> None:
    msg = Message(role='user', content=[Part.from_text('hi')])
    assert msg.content[0].text == 'hi'
    assert_inactive(msg.content[0], active='text')


def test_from_text_none_raises() -> None:
    with pytest.raises(ValidationError):
        Part.from_text(None)  # type: ignore[arg-type]


def test_from_media_empty_url_is_still_media() -> None:
    p = Part.from_media('')
    assert p.media is not None
    assert p.media.url == ''
    assert p.text is None
    assert_inactive(p, active='media')


def test_empty_metadata_dict_is_present_on_dump() -> None:
    msg = Message(role='user', content=[Part.from_text('hi', metadata={})])
    assert msg.model_dump()['content'][0]['metadata'] == {}


def test_from_text_dump_matches_wire_format() -> None:
    msg = Message(role='user', content=[Part.from_text('hello')])
    dumped = msg.model_dump()['content'][0]
    assert dumped == {'text': 'hello'}
    assert 'root' not in dumped


def test_from_media_dump_matches_wire_format() -> None:
    msg = Message(role='user', content=[Part.from_media('https://x', content_type='image/png')])
    dumped = msg.model_dump()['content'][0]
    assert dumped == {'media': {'url': 'https://x', 'contentType': 'image/png'}}
    assert 'root' not in dumped
    assert dumped['media'].get('contentType') == 'image/png'


def test_from_tool_request_dump_omits_unset_input() -> None:
    msg = Message(role='model', content=[Part.from_tool_request(name='lookup')])
    dumped = msg.model_dump()['content'][0]
    assert dumped == {'toolRequest': {'name': 'lookup'}}
    assert 'input' not in dumped['toolRequest']


def test_from_reasoning_dump_is_reasoning_not_text() -> None:
    msg = Message(role='model', content=[Part.from_reasoning('think step by step')])
    dumped = msg.model_dump()['content'][0]
    assert dumped == {'reasoning': 'think step by step'}
    again = Part.model_validate(dumped)
    assert again.reasoning == 'think step by step'
    assert again.text is None


def test_from_custom_and_from_data_dump_different_keys() -> None:
    custom_msg = Message(role='user', content=[Part.from_custom({'a': 1})])
    data_msg = Message(role='user', content=[Part.from_data({'a': 1})])
    assert custom_msg.model_dump()['content'][0] == {'custom': {'a': 1}}
    assert data_msg.model_dump()['content'][0] == {'data': {'a': 1}}


def test_media_part_text_is_none_url_is_on_media() -> None:
    p = Part.from_media('https://example.com/image.png')
    assert p.text is None
    assert p.media is not None
    assert p.media.url == 'https://example.com/image.png'


def test_message_text_skips_reasoning_and_media() -> None:
    msg = Message(
        role='model',
        content=[
            Part.from_reasoning('think'),
            Part.from_text('hello'),
            Part.from_media('https://x'),
        ],
    )
    assert msg.text == 'hello'


def test_resource_wire_part_has_no_public_getters() -> None:
    p = Part.model_validate({'resource': {'uri': 'test://x'}})
    for name in _GETTERS:
        assert getattr(p, name) is None


def test_message_from_text_dict_reads_text() -> None:
    """A wire dict on Message is a Part they can read .text on."""
    msg = Message(role='user', content=[{'text': 'hello'}])
    assert msg.content[0].text == 'hello'
    assert_inactive(msg.content[0], active='text')


def test_document_from_text_dict_reads_text() -> None:
    """A wire dict on Document is a Part they can read .text on."""
    doc = Document(content=[{'text': 'hello'}])
    assert doc.content[0].text == 'hello'
    assert_inactive(doc.content[0], active='text')


def test_empty_part_dict_raises() -> None:
    """{} is not a part."""
    with pytest.raises(ValidationError, match='exactly one'):
        Part.model_validate({})


def test_metadata_only_part_raises() -> None:
    """Metadata without a kind is not a part."""
    with pytest.raises(ValidationError, match='exactly one'):
        Part.model_validate({'metadata': {'source': 'user'}})


def test_null_text_part_raises() -> None:
    """A null text field is not a text part."""
    with pytest.raises(ValidationError, match='exactly one'):
        Part.model_validate({'text': None})


def test_text_and_media_on_text_part_raises() -> None:
    """Caption plus image on one TextPart is two kinds."""
    with pytest.raises(ValidationError, match='exactly one'):
        Part(root=TextPart(text='hi', media=Media(url='https://x')))


def test_part_data_text_and_media_on_message_raises() -> None:
    """A two-kind PartData on a Message is still two kinds."""
    pd = PartData.model_validate({'text': 'hi', 'media': {'url': 'https://x'}})
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[pd])


def test_part_data_text_and_data_on_message_raises() -> None:
    """Caption plus app data on one PartData is two kinds."""
    pd = PartData.model_validate({'text': 'hi', 'data': {'recipe': 1}})
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[pd])


def test_empty_part_data_on_message_raises() -> None:
    """An empty PartData on a Message is not a part."""
    pd = PartData.model_validate({})
    with pytest.raises(ValidationError, match='exactly one'):
        Message(role='user', content=[pd])


def test_document_text_and_media_on_one_part_raises() -> None:
    """Caption plus image on one Document part is two kinds."""
    with pytest.raises(ValidationError, match='exactly one'):
        Document(content=[{'text': 'hi', 'media': {'url': 'https://x'}}])


def test_tool_request_camel_and_snake_is_one_kind() -> None:
    """Both aliases of one tool call are still one kind."""
    p = Part.model_validate({'toolRequest': {'name': 'lookup'}, 'tool_request': {'name': 'lookup'}})
    assert p.tool_request is not None
    assert p.tool_request.name == 'lookup'
    assert_inactive(p, active='tool_request')


def test_part_dump_matches_message_wire() -> None:
    """A standalone Part dump matches the Message wire."""
    text_part = Part.from_text('hello')
    media_part = Part.from_media('https://x', content_type='image/png')
    assert text_part.model_dump() == {'text': 'hello'}
    assert media_part.model_dump() == {'media': {'url': 'https://x', 'contentType': 'image/png'}}
    assert 'root' not in text_part.model_dump()
