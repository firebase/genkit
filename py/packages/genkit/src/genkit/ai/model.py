# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Model type definitions for the Genkit framework.

This module defines the type interfaces for AI models in the Genkit framework.
These types ensure consistent interaction with different AI models and provide
type safety when working with model inputs and outputs.

Example:
    def my_model(request: GenerateRequest) -> GenerateResponse:
        # Model implementation
        return GenerateResponse(...)

    model_fn: ModelFn = my_model
"""

from collections.abc import Callable
from functools import cached_property
from typing import Any

from genkit.core.extract import extract_json
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    Message,
)
from pydantic import Field

# Type alias for a function that takes a GenerateRequest and returns
# a GenerateResponse
type ModelFn = Callable[[GenerateRequest], GenerateResponse]

# These types are duplicated in genkit.ai.formats.types due to circular deps
type MessageParser[T] = Callable[[MessageWrapper], T]
type ChunkParser[T] = Callable[[GenerateResponseChunkWrapper], T]


class MessageWrapper(Message):
    """A helper wrapper class for Message that offer a few utility methods"""

    def __init__(
        self,
        message: Message,
    ):
        super().__init__(
            role=message.role,
            content=message.content,
            metadata=message.metadata,
        )

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the current chunk joined into a single string.

        Returns:
            str: The combined text content from the current chunk.
        """
        return ''.join(
            p.root.text if p.root.text is not None else '' for p in self.content
        )


class GenerateResponseWrapper(GenerateResponse):
    """A helper wrapper class for GenerateResponse that offer a few utility methods"""

    message_parser: MessageParser | None = Field(exclude=True)
    message: MessageWrapper = None

    def __init__(
        self,
        response: GenerateResponse,
        request: GenerateRequest,
        message_parser: MessageParser | None = None,
    ):
        """Initializes a GenerateResponseWrapper instance.

        Args:
            response: The original GenerateResponse object.
            request: The GenerateRequest object associated with the response.
        """
        super().__init__(
            message=MessageWrapper(response.message),
            finish_reason=response.finish_reason,
            finish_message=response.finish_message,
            latency_ms=response.latency_ms,
            usage=response.usage
            if response.usage is not None
            else GenerationUsage(),
            custom=response.custom if response.custom is not None else {},
            request=request,
            candidates=response.candidates,
            message_parser=message_parser,
        )

    def assert_valid(self):
        """Validate that the response is properly structured.

        Raises:
            AssertionError: If the response is not valid.
        """
        # TODO: implement
        pass

    def assert_valid_schema(self):
        """Validate that the response conforms to the expected schema.

        Raises:
            AssertionError: If the response does not conform to the schema.
        """
        # TODO: implement
        pass

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the response joined into a single string.

        Returns:
            str: The combined text content from the response.
        """
        return self.message.text

    @cached_property
    def output(self) -> Any:
        """Parses out JSON data from the text parts of the response.

        Returns:
            Any: The parsed JSON data from the response.
        """
        if self.message_parser:
            return self.message_parser(self.message)
        return extract_json(self.text)


class GenerateResponseChunkWrapper(GenerateResponseChunk):
    """A helper wrapper class for GenerateResponseChunk that offer a few utility methods"""

    previous_chunks: list[GenerateResponseChunk] = Field(exclude=True)
    chunk_parser: ChunkParser | None = Field(exclude=True)

    def __init__(
        self,
        chunk: GenerateResponseChunk,
        previous_chunks: list[GenerateResponseChunk],
        index: int,
        chunk_parser: ChunkParser | None = None,
    ):
        super().__init__(
            role=chunk.role,
            index=index,
            content=chunk.content,
            custom=chunk.custom,
            aggregated=chunk.aggregated,
            previous_chunks=previous_chunks,
            chunk_parser=chunk_parser,
        )

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the current chunk joined into a single string.

        Returns:
            str: The combined text content from the current chunk.
        """
        return ''.join(
            p.root.text if p.root.text is not None else '' for p in self.content
        )

    @cached_property
    def accumulated_text(self) -> str:
        """Returns all text parts from previous chunks plus the latest chunk.

        Returns:
            str: The combined text content from all chunks seen so far.
        """
        if not self.previous_chunks:
            return ''
        atext = ''
        for chunk in self.previous_chunks:
            for p in chunk.content:
                if p.root.text:
                    atext += p.root.text
        return atext + self.text

    @cached_property
    def output(self) -> Any:
        """Parses out JSON data from the accumulated text parts of the response.

        Returns:
            Any: The parsed JSON data from the accumulated chunks.
        """
        if self.chunk_parser:
            return self.chunk_parser(self)
        return extract_json(self.accumulated_text)
