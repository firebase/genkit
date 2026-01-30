# Copyright 2026 Google LLC
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

"""Shared interfaces and typing helpers across blocks."""

from __future__ import annotations

from typing import Generic, TypedDict, TypeVar

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


class OutputConfigDict(TypedDict, total=False):
    """TypedDict for output configuration when passed as a dict."""

    format: str | None
    content_type: str | None
    instructions: bool | str | None
    schema: type | dict[str, object] | None
    constrained: bool | None


class Input(Generic[InputT]):
    """Typed input configuration that preserves schema type information.

    This class provides a type-safe way to configure input schemas for prompts.
    When you pass a Pydantic model as the schema, the prompt's input parameter
    will be properly typed.
    """

    def __init__(self, schema: type[InputT]) -> None:
        """Initialize typed input configuration.

        Args:
            schema: The type/class for structured input.
        """
        self.schema: type[InputT] = schema


class Output(Generic[OutputT]):
    """Typed output configuration that preserves schema type information.

    This class provides a type-safe way to configure output options for generate().
    When you pass a Pydantic model or other type as the schema, the return type
    of generate() will be properly typed.
    """

    def __init__(
        self,
        schema: type[OutputT],
        format: str = 'json',
        content_type: str | None = None,
        instructions: bool | str | None = None,
        constrained: bool | None = None,
    ) -> None:
        """Initialize typed output configuration.

        Args:
            schema: The type/class for structured output.
            format: Output format name. Defaults to 'json'.
            content_type: Optional MIME content type.
            instructions: Optional formatting instructions.
            constrained: Whether to constrain output to schema.
        """
        self.schema: type[OutputT] = schema
        self.format: str = format
        self.content_type: str | None = content_type
        self.instructions: bool | str | None = instructions
        self.constrained: bool | None = constrained

    def to_dict(self) -> OutputConfigDict:
        """Convert to OutputConfigDict for internal use."""
        result: OutputConfigDict = {'schema': self.schema, 'format': self.format}
        if self.content_type is not None:
            result['content_type'] = self.content_type
        if self.instructions is not None:
            result['instructions'] = self.instructions
        if self.constrained is not None:
            result['constrained'] = self.constrained
        return result
