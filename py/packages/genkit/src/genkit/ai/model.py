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
)

# Type alias for a function that takes a GenerateRequest and returns
# a GenerateResponse
type ModelFn = Callable[[GenerateRequest], GenerateResponse]


class GenerateResponseWrapper(GenerateResponse):
    """A helper wrapper class for GenerateResponse that offer a few utility methods"""

    def __init__(self, response: GenerateResponse, request: GenerateRequest):
        """Initializes a GenerateResponseWrapper instance.

        Args:
            response: The original GenerateResponse object.
            request: The GenerateRequest object associated with the response.
        """
        super().__init__(
            message=response.message,
            finish_reason=response.finish_reason,
            finish_message=response.finish_message,
            latency_ms=response.latency_ms,
            usage=response.usage
            if response.usage is not None
            else GenerationUsage(),
            custom=response.custom if response.custom is not None else {},
            request=request,
            candidates=response.candidates,
        )

    def assert_valid(self):
        # TODO: implement
        pass

    def assert_valid_schema(self):
        # TODO: implement
        pass

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the response joined into a single string"""
        return ''.join([
            p.root.text if p.root.text is not None else ''
            for p in self.message.content
        ])

    @cached_property
    def output(self) -> Any:
        """Parses out JSON data from the text parts of the response."""
        return extract_json(self.text)


class GenerateResponseChunkWrapper(GenerateResponseChunk):
    """A helper wrapper class for GenerateResponseChunk that offer a few utility methods"""

    previous_chunks: list[GenerateResponseChunk]

    def __init__(
        self,
        chunk: GenerateResponseChunk,
        previous_chunks: list[GenerateResponseChunk],
        index: str,
    ):
        super().__init__(
            role=chunk.role,
            index=index,
            content=chunk.content,
            custom=chunk.custom,
            aggregated=chunk.aggregated,
            previous_chunks=previous_chunks,
        )

    @cached_property
    def text(self) -> str:
        """Returns all text parts of the current chunk joined into a single string."""
        return ''.join(
            p.root.text if p.root.text is not None else '' for p in self.content
        )

    @cached_property
    def accumulated_text(self) -> str:
        """Returns all text parts from previous chunks plus the latest chunk."""
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
        """Parses out JSON data from the accumulated text parts of the response."""
        return extract_json(self.accumulated_text)
