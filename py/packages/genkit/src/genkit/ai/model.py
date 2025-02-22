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

from genkit.core.schema_types import GenerateRequest, GenerateResponse

# Type alias for a function that takes a GenerateRequest and returns
# a GenerateResponse
ModelFn = Callable[[GenerateRequest], GenerateResponse]
