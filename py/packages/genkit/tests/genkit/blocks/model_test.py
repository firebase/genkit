#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pytest

from genkit.blocks.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    MessageWrapper,
    PartCounts,
    get_basic_usage_stats,
    get_part_counts,
    model_action_metadata,
    text_from_content,
)
from genkit.core.action import ActionMetadata
from genkit.core.typing import (
    Candidate,
    DocumentPart,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    Media,
    MediaPart,
    Message,
    Metadata,
    Part,
    TextPart,
    ToolRequest,
    ToolRequestPart,
)


def test_message_wrapper_text() -> None:
    """Test text property of MessageWrapper."""
    wrapper = MessageWrapper(
        Message(
            role='model',
            content=[Part(root=TextPart(text='hello')), Part(root=TextPart(text=' world'))],
        ),
    )

    assert wrapper.text == 'hello world'


def test_response_wrapper_text() -> None:
    """Test text property of GenerateResponseWrapper."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='hello')), Part(root=TextPart(text=' world'))],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
    )

    assert wrapper.text == 'hello world'


def test_response_wrapper_output() -> None:
    """Test output property of GenerateResponseWrapper."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='{"foo":')), Part(root=TextPart(text='"bar'))],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
    )

    assert wrapper.output == {'foo': 'bar'}


def test_response_wrapper_messages() -> None:
    """Test messages property of GenerateResponseWrapper."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='baz'))],
            )
        ),
        request=GenerateRequest(
            messages=[
                Message(
                    role='user',
                    content=[Part(root=TextPart(text='foo'))],
                ),
                Message(
                    role='tool',
                    content=[Part(root=TextPart(text='bar'))],
                ),
            ],
        ),
    )

    assert wrapper.messages == [
        Message(
            role='user',
            content=[Part(root=TextPart(text='foo'))],
        ),
        Message(
            role='tool',
            content=[Part(root=TextPart(text='bar'))],
        ),
        Message(
            role='model',
            content=[Part(root=TextPart(text='baz'))],
        ),
    ]


def test_response_wrapper_output_uses_parser() -> None:
    """Test that GenerateResponseWrapper uses the provided message_parser."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='{"foo":')), Part(root=TextPart(text='"bar'))],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
        message_parser=lambda x: 'banana',
    )

    assert wrapper.output == 'banana'


def test_chunk_wrapper_text() -> None:
    """Test text property of GenerateResponseChunkWrapper."""
    wrapper = GenerateResponseChunkWrapper(
        chunk=GenerateResponseChunk(content=[Part(root=TextPart(text='hello')), Part(root=TextPart(text=' world'))]),
        index=0,
        previous_chunks=[],
    )

    assert wrapper.text == 'hello world'


def test_chunk_wrapper_accumulated_text() -> None:
    """Test accumulated_text property of GenerateResponseChunkWrapper."""
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[Part(root=TextPart(text=' PS: aliens'))]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(content=[Part(root=TextPart(text='hello')), Part(root=TextPart(text=' '))]),
            GenerateResponseChunk(content=[Part(root=TextPart(text='world!'))]),
        ],
    )

    assert wrapper.accumulated_text == 'hello world! PS: aliens'


def test_chunk_wrapper_output() -> None:
    """Test output property of GenerateResponseChunkWrapper."""
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[Part(root=TextPart(text=', "baz":[1,2,'))]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(content=[Part(root=TextPart(text='{"foo":')), Part(root=TextPart(text='"ba'))]),
            GenerateResponseChunk(content=[Part(root=TextPart(text='r"'))]),
        ],
    )

    assert wrapper.output == {'foo': 'bar', 'baz': [1, 2]}


def test_chunk_wrapper_output_uses_parser() -> None:
    """Test that GenerateResponseChunkWrapper uses the provided chunk_parser."""
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[Part(root=TextPart(text=', "baz":[1,2,'))]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(content=[Part(root=TextPart(text='{"foo":')), Part(root=TextPart(text='"ba'))]),
            GenerateResponseChunk(content=[Part(root=TextPart(text='r"'))]),
        ],
        chunk_parser=lambda x: 'banana',
    )

    assert wrapper.output == 'banana'


@pytest.mark.parametrize(
    'test_parts,expected_part_counts',
    (
        [[], PartCounts()],
        [
            [
                Part(root=MediaPart(media=Media(content_type='image', url=''))),
                Part(root=MediaPart(media=Media(url='data:image'))),
                Part(root=MediaPart(media=Media(content_type='audio', url=''))),
                Part(root=MediaPart(media=Media(url='data:audio'))),
                Part(root=MediaPart(media=Media(content_type='video', url=''))),
                Part(root=MediaPart(media=Media(url='data:video'))),
                Part(root=TextPart(text='test')),
            ],
            PartCounts(
                characters=len('test'),
                audio=2,
                videos=2,
                images=2,
            ),
        ],
    ),
)
def test_get_part_counts(test_parts, expected_part_counts) -> None:
    """Test get_part_counts utility."""
    assert get_part_counts(parts=test_parts) == expected_part_counts


@pytest.mark.parametrize(
    'test_input,test_response,expected_output',
    (
        [
            [],
            [],
            GenerationUsage(
                input_images=0,
                input_videos=0,
                input_characters=0,
                input_audio_files=0,
                output_audio_files=0,
                output_characters=0,
                output_images=0,
                output_videos=0,
            ),
        ],
        [
            [
                Message(
                    role='user',
                    content=[
                        Part(root=TextPart(text='1')),
                        Part(root=TextPart(text='2')),
                    ],
                ),
                Message(
                    role='user',
                    content=[
                        Part(root=MediaPart(media=Media(content_type='image', url=''))),
                        Part(root=MediaPart(media=Media(url='data:image'))),
                        Part(root=MediaPart(media=Media(content_type='audio', url=''))),
                        Part(root=MediaPart(media=Media(url='data:audio'))),
                        Part(root=MediaPart(media=Media(content_type='video', url=''))),
                        Part(root=MediaPart(media=Media(url='data:video'))),
                    ],
                ),
            ],
            Message(
                role='user',
                content=[
                    Part(root=TextPart(text='3')),
                    Part(root=MediaPart(media=Media(content_type='image', url=''))),
                    Part(root=MediaPart(media=Media(url='data:image'))),
                    Part(root=MediaPart(media=Media(content_type='audio', url=''))),
                    Part(root=MediaPart(media=Media(url='data:audio'))),
                    Part(root=MediaPart(media=Media(content_type='video', url=''))),
                    Part(root=MediaPart(media=Media(url='data:video'))),
                ],
            ),
            GenerationUsage(
                input_images=2,
                input_videos=2,
                input_characters=2,
                input_audio_files=2,
                output_audio_files=2,
                output_characters=1,
                output_images=2,
                output_videos=2,
            ),
        ],
        [
            [
                Message(
                    role='user',
                    content=[
                        Part(root=TextPart(text='1')),
                        Part(root=TextPart(text='2')),
                    ],
                ),
            ],
            [
                Candidate(
                    index=0,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=TextPart(text='3')),
                        ],
                    ),
                ),
                Candidate(
                    index=1,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(content_type='image', url=''))),
                        ],
                    ),
                ),
                Candidate(
                    index=2,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:image'))),
                        ],
                    ),
                ),
                Candidate(
                    index=3,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(content_type='audio', url=''))),
                        ],
                    ),
                ),
                Candidate(
                    index=4,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:audio'))),
                        ],
                    ),
                ),
                Candidate(
                    index=5,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(content_type='video', url=''))),
                        ],
                    ),
                ),
                Candidate(
                    index=6,
                    finish_reason=FinishReason.STOP,
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:video'))),
                        ],
                    ),
                ),
            ],
            GenerationUsage(
                input_images=0,
                input_videos=0,
                input_characters=2,
                input_audio_files=0,
                output_audio_files=2,
                output_characters=1,
                output_images=2,
                output_videos=2,
            ),
        ],
    ),
)
def test_get_basic_usage_stats(test_input, test_response, expected_output) -> None:
    """Test get_basic_usage_stats utility."""
    assert get_basic_usage_stats(input_=test_input, response=test_response) == expected_output


def test_response_wrapper_tool_requests() -> None:
    """Test tool_requests property of GenerateResponseWrapper."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='bar'))],
            )
        ),
        request=GenerateRequest(
            messages=[
                Message(
                    role='user',
                    content=[Part(root=TextPart(text='foo'))],
                ),
            ],
        ),
    )

    assert wrapper.tool_requests == []

    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[
                    Part(root=ToolRequestPart(tool_request=ToolRequest(name='tool', input={'abc': 3}))),
                    Part(root=TextPart(text='bar')),
                ],
            )
        ),
        request=GenerateRequest(
            messages=[
                Message(
                    role='user',
                    content=[Part(root=TextPart(text='foo'))],
                ),
            ],
        ),
    )

    assert wrapper.tool_requests == [ToolRequestPart(tool_request=ToolRequest(name='tool', input={'abc': 3}))]


def test_response_wrapper_interrupts() -> None:
    """Test interrupts property of GenerateResponseWrapper."""
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[Part(root=TextPart(text='bar'))],
            )
        ),
        request=GenerateRequest(
            messages=[
                Message(
                    role='user',
                    content=[Part(root=TextPart(text='foo'))],
                ),
            ],
        ),
    )

    assert wrapper.interrupts == []

    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[
                    Part(root=ToolRequestPart(tool_request=ToolRequest(name='tool1', input={'abc': 3}))),
                    Part(
                        root=ToolRequestPart(
                            tool_request=ToolRequest(name='tool2', input={'bcd': 4}),
                            metadata=Metadata(root={'interrupt': {'banana': 'yes'}}),
                        )
                    ),
                    Part(root=TextPart(text='bar')),
                ],
            )
        ),
        request=GenerateRequest(
            messages=[
                Message(
                    role='user',
                    content=[Part(root=TextPart(text='foo'))],
                ),
            ],
        ),
    )

    assert wrapper.interrupts == [
        ToolRequestPart(
            tool_request=ToolRequest(name='tool2', input={'bcd': 4}),
            metadata=Metadata(root={'interrupt': {'banana': 'yes'}}),
        )
    ]


def test_model_action_metadata():
    """Test for model_action_metadata."""
    action_metadata = model_action_metadata(
        name='test_model',
        info={'label': 'test_label'},
        config_schema=None,
    )

    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.input_json_schema is not None
    assert action_metadata.output_json_schema is not None
    assert action_metadata.metadata == {'model': {'customOptions': None, 'label': 'test_label'}}


def test_text_from_content_with_parts() -> None:
    """Test text_from_content with list of Part objects."""
    content = [Part(root=TextPart(text='hello')), Part(root=TextPart(text=' world'))]
    assert text_from_content(content) == 'hello world'


def test_text_from_content_with_document_parts() -> None:
    """Test text_from_content with list of DocumentPart objects."""
    content = [DocumentPart(root=TextPart(text='doc1')), DocumentPart(root=TextPart(text=' doc2'))]
    assert text_from_content(content) == 'doc1 doc2'


def test_text_from_content_with_mixed_parts() -> None:
    """Test text_from_content with mixed Part and DocumentPart objects."""
    content = [
        Part(root=TextPart(text='part')),
        DocumentPart(root=TextPart(text=' text')),
    ]
    assert text_from_content(content) == 'part text'


def test_text_from_content_with_empty_list() -> None:
    """Test text_from_content with empty list."""
    assert text_from_content([]) == ''


def test_text_from_content_with_none_text() -> None:
    """Test text_from_content handles parts without text content."""
    content = [
        Part(root=TextPart(text='hello')),
        Part(root=MediaPart(media=Media(url='http://example.com/image.png'))),
        Part(root=TextPart(text=' world')),
    ]
    assert text_from_content(content) == 'hello world'
