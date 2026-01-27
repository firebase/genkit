#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Text format."""

from genkit.blocks.formats.text import TextFormat
from genkit.blocks.model import GenerateResponseChunkWrapper, MessageWrapper
from genkit.core.typing import GenerateResponseChunk, Message, Part, TextPart


class TestTextFormatStreaming:
    """Test streaming chunk parsing."""

    def test_emits_text_chunks_as_they_arrive(self) -> None:
        """Test that text chunks return only the current chunk's text."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        # Chunk 1: "Hello"
        chunk1 = GenerateResponseChunk(content=[Part(root=TextPart(text='Hello'))])
        result1 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk1, index=0, previous_chunks=[]))
        assert result1 == 'Hello'

        # Chunk 2: " world" - should return only this chunk's text, not accumulated
        chunk2 = GenerateResponseChunk(content=[Part(root=TextPart(text=' world'))])
        result2 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk2, index=0, previous_chunks=[chunk1]))
        assert result2 == ' world'

    def test_handles_empty_chunks(self) -> None:
        """Test handling empty text chunks."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        chunk = GenerateResponseChunk(content=[Part(root=TextPart(text=''))])
        result = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk, index=0, previous_chunks=[]))
        assert result == ''


class TestTextFormatMessage:
    """Test complete message parsing."""

    def test_parses_complete_text_response(self) -> None:
        """Test parsing a complete text response."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        result = fmt.parse_message(
            MessageWrapper(Message(role='model', content=[Part(root=TextPart(text='Hello world'))]))
        )
        assert result == 'Hello world'

    def test_handles_empty_response(self) -> None:
        """Test parsing an empty response."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        result = fmt.parse_message(MessageWrapper(Message(role='model', content=[Part(root=TextPart(text=''))])))
        assert result == ''

    def test_handles_multiline_text(self) -> None:
        """Test parsing multiline text."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        result = fmt.parse_message(
            MessageWrapper(Message(role='model', content=[Part(root=TextPart(text='Line 1\nLine 2\nLine 3'))]))
        )
        assert result == 'Line 1\nLine 2\nLine 3'


class TestTextFormatConfig:
    """Test format configuration."""

    def test_has_correct_content_type(self) -> None:
        """Test that content type is text/plain."""
        text_fmt = TextFormat()
        assert text_fmt.config.content_type == 'text/plain'

    def test_has_no_constrained(self) -> None:
        """Test that constrained is not set."""
        text_fmt = TextFormat()
        assert text_fmt.config.constrained is None


class TestTextFormatInstructions:
    """Test instruction generation."""

    def test_no_instructions(self) -> None:
        """Test that text format has no instructions."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle(None)

        assert fmt.instructions is None

    def test_no_instructions_with_schema(self) -> None:
        """Test that text format ignores schema for instructions."""
        text_fmt = TextFormat()
        fmt = text_fmt.handle({'type': 'string'})

        assert fmt.instructions is None
