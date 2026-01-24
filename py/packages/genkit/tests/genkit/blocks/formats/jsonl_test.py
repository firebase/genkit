#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the JSONL format."""

import pytest

from genkit.blocks.formats.jsonl import JsonlFormat
from genkit.blocks.model import GenerateResponseChunkWrapper, MessageWrapper
from genkit.core.error import GenkitError
from genkit.core.typing import GenerateResponseChunk, Message, Part, TextPart


class TestJsonlFormatStreaming:
    """Test streaming chunk parsing."""

    def test_emits_complete_json_objects_as_they_arrive(self) -> None:
        """Test that complete objects are emitted as they arrive in chunks."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        # Chunk 1: first complete object
        chunk1 = GenerateResponseChunk(content=[Part(root=TextPart(text='{"id": 1, "name": "first"}\n'))])
        result1 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk1, index=0, previous_chunks=[]))
        assert result1 == [{'id': 1, 'name': 'first'}]

        # Chunk 2: second object complete, third starts
        chunk2 = GenerateResponseChunk(content=[Part(root=TextPart(text='{"id": 2, "name": "second"}\n{"id": 3'))])
        result2 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk2, index=0, previous_chunks=[chunk1]))
        assert result2 == [{'id': 2, 'name': 'second'}]

        # Chunk 3: third object completes
        chunk3 = GenerateResponseChunk(content=[Part(root=TextPart(text=', "name": "third"}\n'))])
        result3 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk3, index=0, previous_chunks=[chunk1, chunk2]))
        assert result3 == [{'id': 3, 'name': 'third'}]

    def test_handles_single_object(self) -> None:
        """Test parsing a single object in one chunk."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        chunk = GenerateResponseChunk(content=[Part(root=TextPart(text='{"id": 1, "name": "single"}\n'))])
        result = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk, index=0, previous_chunks=[]))
        assert result == [{'id': 1, 'name': 'single'}]

    def test_handles_preamble_with_code_fence(self) -> None:
        """Test parsing JSONL with preamble text and code fence."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        # Chunk 1: preamble
        chunk1 = GenerateResponseChunk(content=[Part(root=TextPart(text='Here are the objects:\n\n```\n'))])
        result1 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk1, index=0, previous_chunks=[]))
        assert result1 == []

        # Chunk 2: actual data
        chunk2 = GenerateResponseChunk(content=[Part(root=TextPart(text='{"id": 1, "name": "item"}\n```'))])
        result2 = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk2, index=0, previous_chunks=[chunk1]))
        assert result2 == [{'id': 1, 'name': 'item'}]

    def test_ignores_non_object_lines(self) -> None:
        """Test that non-object lines are ignored."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        chunk = GenerateResponseChunk(
            content=[Part(root=TextPart(text='First object:\n{"id": 1}\nSecond object:\n{"id": 2}\n'))]
        )
        result = fmt.parse_chunk(GenerateResponseChunkWrapper(chunk, index=0, previous_chunks=[]))
        assert result == [{'id': 1}, {'id': 2}]


class TestJsonlFormatMessage:
    """Test complete message parsing."""

    def test_parses_complete_jsonl_response(self) -> None:
        """Test parsing a complete JSONL response."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        result = fmt.parse_message(
            MessageWrapper(
                Message(role='model', content=[Part(root=TextPart(text='{"id": 1, "name": "test"}\n{"id": 2}\n'))])
            )
        )
        assert result == [{'id': 1, 'name': 'test'}, {'id': 2}]

    def test_handles_empty_response(self) -> None:
        """Test parsing an empty response."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        result = fmt.parse_message(MessageWrapper(Message(role='model', content=[Part(root=TextPart(text=''))])))
        assert result == []

    def test_parses_jsonl_with_preamble_and_code_fence(self) -> None:
        """Test parsing JSONL with preamble and code fence."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object'}})

        result = fmt.parse_message(
            MessageWrapper(
                Message(
                    role='model',
                    content=[Part(root=TextPart(text='Here are the objects:\n\n```\n{"id": 1}\n{"id": 2}\n```'))],
                )
            )
        )
        assert result == [{'id': 1}, {'id': 2}]


class TestJsonlFormatErrors:
    """Test error handling."""

    def test_throws_error_for_non_array_schema_type(self) -> None:
        """Test that non-array schema type raises error."""
        jsonl_fmt = JsonlFormat()

        with pytest.raises(GenkitError) as exc_info:
            jsonl_fmt.handle({'type': 'string'})
        assert "Must supply an 'array' schema type" in str(exc_info.value)

    def test_throws_error_for_array_with_non_object_items(self) -> None:
        """Test that array with non-object items raises error."""
        jsonl_fmt = JsonlFormat()

        with pytest.raises(GenkitError) as exc_info:
            jsonl_fmt.handle({'type': 'array', 'items': {'type': 'string'}})
        assert "containing 'object' items" in str(exc_info.value)


class TestJsonlFormatInstructions:
    """Test instruction generation."""

    def test_generates_instructions_with_items_schema(self) -> None:
        """Test that instructions include items schema."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle({'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'number'}}}})

        assert fmt.instructions is not None
        assert 'Output should be JSONL format' in fmt.instructions
        assert 'newline' in fmt.instructions

    def test_no_instructions_without_items(self) -> None:
        """Test that no instructions are generated without items schema."""
        jsonl_fmt = JsonlFormat()
        fmt = jsonl_fmt.handle(None)

        assert fmt.instructions is None
