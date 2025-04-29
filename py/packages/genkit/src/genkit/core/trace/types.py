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

"""Telemetry and tracing types for the Genkit framework.

This module defines the core tracing types for the Genkit framework.

Genkit flows are instrumented to trace key data points, primarily the inputs
sent to and the outputs received from Language Learning Models (LLMs) or
other models.  Outputs may be streamed as chunks. This module establishes
how these interactions are recorded and exported for observability.

Key Features:

-   **GenkitSpan Class:** Provides a core class, `GenkitSpan`, for representing
    and exporting telemetry data related to Genkit operations.  This class
    is intended for internal use by the Genkit framework.
"""

import json
from collections.abc import Mapping
from typing import Any

import structlog
from opentelemetry import trace as trace_api
from opentelemetry.util import types
from pydantic import BaseModel

ATTR_PREFIX = 'genkit'

logger = structlog.get_logger(__name__)


class GenkitSpan:
    """Light wrapper for Span, specific to Genkit."""

    is_root: bool
    _span: trace_api.Span

    def __init__(self, span: trace_api.Span, labels: dict[str, str] | None = None):
        """Create GenkitSpan."""
        self._span = span
        parent = span.parent
        self.is_root = False
        if parent is None:
            self.is_root = True
        if labels is not None:
            self.set_attributes(labels)

    def __getattr__(self, name) -> Any:
        """Passthrough for all OpenTelemetry Span attributes."""
        return getattr(self._span, name)

    def set_genkit_attribute(self, key: str, value: types.AttributeValue) -> None:
        """Set Genkit specific attribute, with the `genkit` prefix."""
        if key == 'metadata' and isinstance(value, dict) and value:
            for meta_key, meta_value in value.items():
                self._span.set_attribute(f'{ATTR_PREFIX}:metadata:{meta_key}', str(meta_value))
        elif isinstance(value, dict):
            self._span.set_attribute(f'{ATTR_PREFIX}:{key}', json.dumps(value))
        else:
            self._span.set_attribute(f'{ATTR_PREFIX}:{key}', str(value))

    def set_genkit_attributes(self, attributes: Mapping[str, types.AttributeValue]) -> None:
        """Set Genkit specific attributes, with the `genkit` prefix."""
        for key, value in attributes.items():
            self.set_genkit_attribute(key, value)

    @property
    def span_id(self) -> str:
        """Returns the span_id."""
        return str(self._span.get_span_context().span_id)

    @property
    def trace_id(self) -> str:
        """Returns the trace_id."""
        return str(self._span.get_span_context().trace_id)

    def set_input(self, input: Any) -> None:
        """Set Genkit Span input, visible in the trace viewer."""
        value = None
        if isinstance(input, BaseModel):
            value = input.model_dump_json(by_alias=True, exclude_none=True)
        else:
            value = json.dumps(input)
        self.set_genkit_attribute('input', value)

    def set_output(self, output: Any) -> None:
        """Set Genkit Span output, visible in the trace viewer."""
        value = None
        if isinstance(output, BaseModel):
            value = output.model_dump_json(by_alias=True, exclude_none=True)
        else:
            value = json.dumps(output)
        self.set_genkit_attribute('output', value)
