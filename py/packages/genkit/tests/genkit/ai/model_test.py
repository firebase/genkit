#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pytest
from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    MessageWrapper,
    PartCounts,
    get_basic_usage_stats,
    get_part_counts,
)
from genkit.core.typing import (
    Candidate,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    Media,
    MediaPart,
    Message,
    Part,
    TextPart,
)


def test_message_wrapper_text() -> None:
    wrapper = MessageWrapper(
        Message(
            role='model',
            content=[TextPart(text='hello'), TextPart(text=' world')],
        ),
    )

    assert wrapper.text == 'hello world'


def test_response_wrapper_text() -> None:
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[TextPart(text='hello'), TextPart(text=' world')],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
    )

    assert wrapper.text == 'hello world'


def test_response_wrapper_output() -> None:
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[TextPart(text='{"foo":'), TextPart(text='"bar')],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
    )

    assert wrapper.output == {'foo': 'bar'}


def test_response_wrapper_output_uses_parser() -> None:
    wrapper = GenerateResponseWrapper(
        response=GenerateResponse(
            message=Message(
                role='model',
                content=[TextPart(text='{"foo":'), TextPart(text='"bar')],
            )
        ),
        request=GenerateRequest(
            messages=[],  # doesn't matter for now
        ),
        message_parser=lambda x: 'banana',
    )

    assert wrapper.output == 'banana'


def test_chunk_wrapper_text() -> None:
    wrapper = GenerateResponseChunkWrapper(
        chunk=GenerateResponseChunk(
            content=[TextPart(text='hello'), TextPart(text=' world')]
        ),
        index=0,
        previous_chunks=[],
    )

    assert wrapper.text == 'hello world'


def test_chunk_wrapper_accumulated_text() -> None:
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[TextPart(text=' PS: aliens')]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(
                content=[TextPart(text='hello'), TextPart(text=' ')]
            ),
            GenerateResponseChunk(content=[TextPart(text='world!')]),
        ],
    )

    assert wrapper.accumulated_text == 'hello world! PS: aliens'


def test_chunk_wrapper_output() -> None:
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[TextPart(text=', "baz":[1,2,')]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(
                content=[TextPart(text='{"foo":'), TextPart(text='"ba')]
            ),
            GenerateResponseChunk(content=[TextPart(text='r"')]),
        ],
    )

    assert wrapper.output == {'foo': 'bar', 'baz': [1, 2]}


def test_chunk_wrapper_output_uses_parser() -> None:
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[TextPart(text=', "baz":[1,2,')]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(
                content=[TextPart(text='{"foo":'), TextPart(text='"ba')]
            ),
            GenerateResponseChunk(content=[TextPart(text='r"')]),
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
    assert get_part_counts(parts=test_parts) == expected_part_counts


@pytest.mark.parametrize(
    'test_input,test_response,expected_output',
    (
        [
            [],
            [],
            GenerationUsage(
                inputImages=0,
                inputVideos=0,
                inputCharacters=0,
                inputAudioFiles=0,
                outputAudioFiles=0,
                outputCharacters=0,
                outputImages=0,
                outputVideos=0,
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
                        Part(
                            root=MediaPart(
                                media=Media(content_type='image', url='')
                            )
                        ),
                        Part(root=MediaPart(media=Media(url='data:image'))),
                        Part(
                            root=MediaPart(
                                media=Media(content_type='audio', url='')
                            )
                        ),
                        Part(root=MediaPart(media=Media(url='data:audio'))),
                        Part(
                            root=MediaPart(
                                media=Media(content_type='video', url='')
                            )
                        ),
                        Part(root=MediaPart(media=Media(url='data:video'))),
                    ],
                ),
            ],
            Message(
                role='user',
                content=[
                    Part(root=TextPart(text='3')),
                    Part(
                        root=MediaPart(
                            media=Media(content_type='image', url='')
                        )
                    ),
                    Part(root=MediaPart(media=Media(url='data:image'))),
                    Part(
                        root=MediaPart(
                            media=Media(content_type='audio', url='')
                        )
                    ),
                    Part(root=MediaPart(media=Media(url='data:audio'))),
                    Part(
                        root=MediaPart(
                            media=Media(content_type='video', url='')
                        )
                    ),
                    Part(root=MediaPart(media=Media(url='data:video'))),
                ],
            ),
            GenerationUsage(
                inputImages=2,
                inputVideos=2,
                inputCharacters=2,
                inputAudioFiles=2,
                outputAudioFiles=2,
                outputCharacters=1,
                outputImages=2,
                outputVideos=2,
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
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(root=TextPart(text='3')),
                        ],
                    ),
                ),
                Candidate(
                    index=1,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(
                                root=MediaPart(
                                    media=Media(content_type='image', url='')
                                )
                            ),
                        ],
                    ),
                ),
                Candidate(
                    index=2,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:image'))),
                        ],
                    ),
                ),
                Candidate(
                    index=3,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(
                                root=MediaPart(
                                    media=Media(content_type='audio', url='')
                                )
                            ),
                        ],
                    ),
                ),
                Candidate(
                    index=4,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:audio'))),
                        ],
                    ),
                ),
                Candidate(
                    index=5,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(
                                root=MediaPart(
                                    media=Media(content_type='video', url='')
                                )
                            ),
                        ],
                    ),
                ),
                Candidate(
                    index=6,
                    finishReason='stop',
                    message=Message(
                        role='user',
                        content=[
                            Part(root=MediaPart(media=Media(url='data:video'))),
                        ],
                    ),
                ),
            ],
            GenerationUsage(
                inputImages=0,
                inputVideos=0,
                inputCharacters=2,
                inputAudioFiles=0,
                outputAudioFiles=2,
                outputCharacters=1,
                outputImages=2,
                outputVideos=2,
            ),
        ],
    ),
)
def test_get_basic_usage_stats(
    test_input, test_response, expected_output
) -> None:
    assert (
        get_basic_usage_stats(input_=test_input, response=test_response)
        == expected_output
    )
