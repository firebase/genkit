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

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import cached_property
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from genkit.core.action import ActionRunContext
from genkit.core.extract import extract_json
from genkit.core.typing import (
    Candidate,
    DocumentPart,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
    Message,
    Part,
    ToolRequestPart,
)

# type ModelFn = Callable[[GenerateRequest], GenerateResponse]
ModelFn = Callable[[GenerateRequest], GenerateResponse]

# These types are duplicated in genkit.blocks.formats.types due to circular deps
T = TypeVar('T')
# type MessageParser[T] = Callable[[MessageWrapper], T]
MessageParser = Callable[['MessageWrapper'], T]
# type ChunkParser[T] = Callable[[GenerateResponseChunkWrapper], T]
ChunkParser = Callable[['GenerateResponseChunkWrapper'], T]


# type ModelMiddlewareNext = Callable[[GenerateRequest, ActionRunContext], Awaitable[GenerateResponse]]
ModelMiddlewareNext = Callable[[GenerateRequest, ActionRunContext], Awaitable[GenerateResponse]]
# type ModelMiddleware = Callable[
#     [GenerateRequest, ActionRunContext, ModelMiddlewareNext],
#     Awaitable[GenerateResponse],
# ]
ModelMiddleware = Callable[
    [GenerateRequest, ActionRunContext, ModelMiddlewareNext],
    Awaitable[GenerateResponse],
]


class MessageWrapper(Message):
    """A wrapper around the base Message type providing utility methods.

    This class extends the standard `Message` by adding convenient cached properties
    like `text` (for concatenated text content) and `tool_requests`.
    It stores the original message in the `_original_message` attribute.
    """

    def __init__(
        self,
        message: Message,
    ):
        """Initializes the MessageWrapper.

        Args:
            message: The original Message object to wrap.
        """
        super().__init__(
            role=message.role,
            content=message.content,
            metadata=message.metadata,
        )
        self._original_message = message

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the current chunk joined into a single string.

        Returns:
            str: The combined text content from the current chunk.
        """
        return text_from_message(self)

    @cached_property
    def tool_requests(self) -> list[ToolRequestPart]:
        """Returns all tool request parts of the response as a list.

        Returns:
            list[ToolRequestPart]: list of tool requests present in this response.
        """
        return [p.root for p in self.content if isinstance(p.root, ToolRequestPart)]

    @cached_property
    def interrupts(self) -> list[ToolRequestPart]:
        """Returns all interrupted tool request parts of the message as a list.

        Returns:
            list[ToolRequestPart]: list of interrupted tool requests.
        """
        return [p for p in self.tool_requests if p.metadata and p.metadata.root.get('interrupt')]


class GenerateResponseWrapper(GenerateResponse):
    """A wrapper around GenerateResponse providing utility methods.

    Extends the base `GenerateResponse` with cached properties (`text`, `output`,
    `messages`, `tool_requests`) and methods for validation (`assert_valid`,
    `assert_valid_schema`). It also handles optional message/chunk parsing.
    """

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
            message_parser: An optional function to parse the output from the message.
        """
        super().__init__(
            message=MessageWrapper(response.message)
            if not isinstance(response.message, MessageWrapper)
            else response.message,
            finish_reason=response.finish_reason,
            finish_message=response.finish_message,
            latency_ms=response.latency_ms,
            usage=response.usage if response.usage is not None else GenerationUsage(),
            custom=response.custom if response.custom is not None else {},
            request=request,
            candidates=response.candidates,
            message_parser=message_parser,
        )

    def assert_valid(self):
        """Validates the basic structure of the response.

        Note: This method is currently a placeholder (TODO).

        Raises:
            AssertionError: If the response structure is considered invalid.
        """
        # TODO: implement
        pass

    def assert_valid_schema(self):
        """Validates that the response message conforms to any specified output schema.

        Note: This method is currently a placeholder (TODO).

        Raises:
            AssertionError: If the response message does not conform to the schema.
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

    @cached_property
    def messages(self) -> list[Message]:
        """Returns all messages of the response, including request messages as a list.

        Returns:
            list[Message]: list of messages.
        """
        return [
            *(self.request.messages if self.request else []),
            self.message._original_message,
        ]

    @cached_property
    def tool_requests(self) -> list[ToolRequestPart]:
        """Returns all tool request parts of the response as a list.

        Returns:
            list[ToolRequestPart]: list of tool requests present in this response.
        """
        return self.message.tool_requests

    @cached_property
    def interrupts(self) -> list[ToolRequestPart]:
        """Returns all interrupted tool request parts of the response as a list.

        Returns:
            list[ToolRequestPart]: list of interrupted tool requests.
        """
        return self.message.interrupts


class GenerateResponseChunkWrapper(GenerateResponseChunk):
    """A wrapper around GenerateResponseChunk providing utility methods.

    Extends the base `GenerateResponseChunk` with cached properties for accessing
    the text content of the current chunk (`text`), the accumulated text from all
    previous chunks including the current one (`accumulated_text`), and parsed
    output from the accumulated text (`output`). It also stores previous chunks.
    """

    previous_chunks: list[GenerateResponseChunk] = Field(exclude=True)
    chunk_parser: ChunkParser | None = Field(exclude=True)

    def __init__(
        self,
        chunk: GenerateResponseChunk,
        previous_chunks: list[GenerateResponseChunk],
        index: int,
        chunk_parser: ChunkParser | None = None,
    ):
        """Initializes the GenerateResponseChunkWrapper.

        Args:
            chunk: The raw GenerateResponseChunk to wrap.
            previous_chunks: A list of preceding chunks in the stream.
            index: The index of this chunk in the sequence of messages/chunks.
            chunk_parser: An optional function to parse the output from the chunk.
        """
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
        return ''.join(p.root.text if p.root.text is not None else '' for p in self.content)

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


class PartCounts(BaseModel):
    """Stores counts of different types of media parts.

    Attributes:
        characters: Total number of characters in text parts.
        images: Total number of image parts.
        videos: Total number of video parts.
        audio: Total number of audio parts.
    """

    characters: int = 0
    images: int = 0
    videos: int = 0
    audio: int = 0


def text_from_message(msg: Message) -> str:
    """Extracts and concatenates text content from all parts of a Message.

    Args:
        msg: The Message object.

    Returns:
        A single string containing all text found in the message parts.
    """
    return text_from_content(msg.content)


def text_from_content(content: list[Part]) -> str:
    """Extracts and concatenates text content from a list of Parts.

    Args:
        content: A list of Part objects.

    Returns:
        A single string containing all text found in the parts.
    """
    return ''.join(
        p.root.text if (isinstance(p, Part) or isinstance(p, DocumentPart)) and p.root.text is not None else ''
        for p in content
    )


def get_basic_usage_stats(input_: list[Message], response: Message | list[Candidate]) -> GenerationUsage:
    """Calculates basic usage statistics based on input and output messages/candidates.

    Counts characters, images, videos, and audio files for both input and output.

    Args:
        input_: A list of input Message objects.
        response: Either a single output Message object or a list of Candidate objects.

    Returns:
        A GenerationUsage object populated with the calculated counts.
    """
    request_parts = []

    for msg in input_:
        request_parts.extend(msg.content)

    response_parts = []
    if isinstance(response, list):
        for candidate in response:
            response_parts.extend(candidate.message.content)
    else:
        response_parts = response.content

    input_counts = get_part_counts(parts=request_parts)
    output_counts = get_part_counts(parts=response_parts)

    return GenerationUsage(
        input_characters=input_counts.characters,
        input_images=input_counts.images,
        input_videos=input_counts.videos,
        input_audio_files=input_counts.audio,
        output_characters=output_counts.characters,
        output_images=output_counts.images,
        output_videos=output_counts.videos,
        output_audio_files=output_counts.audio,
    )


def get_part_counts(parts: list[Part]) -> PartCounts:
    """Counts the occurrences of different media types within a list of Parts.

    Iterates through the parts, summing character lengths and counting image,
    video, and audio parts based on content type or data URL prefix.

    Args:
        parts: A list of Part objects to analyze.

    Returns:
        A PartCounts object containing the aggregated counts.
    """
    part_counts = PartCounts()

    for part in parts:
        part_counts.characters += len(part.root.text) if part.root.text else 0

        media = part.root.media

        if media:
            content_type = media.content_type or ''
            url = media.url or ''
            is_image = content_type.startswith('image') or url.startswith('data:image')
            is_video = content_type.startswith('video') or url.startswith('data:video')
            is_audio = content_type.startswith('audio') or url.startswith('data:audio')

            part_counts.images += 1 if is_image else 0
            part_counts.videos += 1 if is_video else 0
            part_counts.audio += 1 if is_audio else 0

    return part_counts
