#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
)
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    TextPart,
)


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
        GenerateResponseChunk(content=[TextPart(text='doesn not matter')]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(
                content=[TextPart(text='hello'), TextPart(text=' ')]
            ),
            GenerateResponseChunk(content=[TextPart(text='world')]),
        ],
    )

    assert wrapper.accumulated_text == 'hello world'


def test_chunk_wrapper_output() -> None:
    wrapper = GenerateResponseChunkWrapper(
        GenerateResponseChunk(content=[TextPart(text='doesn not matter')]),
        index=0,
        previous_chunks=[
            GenerateResponseChunk(
                content=[TextPart(text='{"foo":'), TextPart(text='"ba')]
            ),
            GenerateResponseChunk(content=[TextPart(text='r"')]),
        ],
    )

    assert wrapper.output == {'foo': 'bar'}
