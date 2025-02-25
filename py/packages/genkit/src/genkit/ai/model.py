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

from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationUsage,
)

# Type alias for a function that takes a GenerateRequest and returns
# a GenerateResponse
ModelFn = Callable[[GenerateRequest], GenerateResponse]


class GenerateResponseWrapper(GenerateResponse):
    def __init__(self, response: GenerateResponse, request: GenerateRequest):
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

    def text(self):
        return ''.join([
            p.root.text if p.root.text is not None else ''
            for p in self.message.content
        ])

    def output(self):
        # TODO: implement
        pass


class GenerateResponseChunkWrapper(GenerateResponseChunk):
    def __init__(
        self,
        chunk: GenerateResponseChunk,
        index: int,
        prevChunks: list[GenerateResponseChunk],
    ):
        super().__init__(
            role=chunk.role,
            index=chunk.index,
            content=chunk.content,
            custom=chunk.custom,
            aggregated=chunk.aggregated,
        )

    def text(self):
        return ''.join([
            p.root.text if p.root.text is not None else '' for p in self.content
        ])
