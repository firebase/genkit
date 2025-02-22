# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Prompt management and templating for the Genkit framework.

This module provides types and utilities for managing prompts and templates
used with AI models in the Genkit framework. It enables consistent prompt
generation and management across different parts of the application.
"""

from collections.abc import Callable
from typing import Any

from genkit.core.schema_types import GenerateRequest

# Type alias for a function that takes optional context and returns
# a GenerateRequest
PromptFn = Callable[[Any | None], GenerateRequest]
