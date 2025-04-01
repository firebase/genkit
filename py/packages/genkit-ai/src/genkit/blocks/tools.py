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

from typing import Any

from genkit.core.action import ActionRunContext
from genkit.core.typing import Part, ToolRequestPart, ToolResponse


class ToolRunContext(ActionRunContext):
    """Provides context specific to the execution of a Genkit tool.

    Inherits from ActionRunContext and adds functionality relevant to tools,
    such as interrupting the tool's execution flow.
    """

    def __init__(
        self,
        ctx: ActionRunContext,
    ):
        """Initializes the ToolRunContext.

        Args:
            ctx: The parent ActionRunContext.
        """
        super().__init__(
            on_chunk=ctx._on_chunk if ctx.is_streaming else None,
            context=ctx.context,
        )

    def interrupt(self, metadata: dict[str, Any] | None = None):
        """Interrupts the current tool execution.

        Raises a ToolInterruptError, which can be caught by the generation
        process to handle controlled interruptions (e.g., asking the user for
        clarification).

        Args:
            metadata: Optional metadata to associate with the interrupt.
        """
        raise ToolInterruptError(metadata=metadata)


# TODO: make this extend GenkitError once it has INTERRUPTED status
class ToolInterruptError(Exception):
    """Exception raised to signal a controlled interruption of tool execution.

    This is used as a flow control mechanism within the generation process,
    allowing a tool to pause execution and potentially signal back to the
    calling flow (e.g., to request user input or clarification) without
    causing a hard failure.
    """

    def __init__(self, metadata: dict[str, Any]):
        """Initializes the ToolInterruptError.

        Args:
            metadata: Metadata associated with the interruption.
        """
        self.metadata = metadata


def tool_response(
    interrupt: Part | ToolRequestPart,
    response_data: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> Part:
    """Constructs a ToolResponse Part, typically for an interrupted request.

    This is often used when a tool's execution was interrupted (e.g., via
    ToolInterruptError) and a specific response needs to be formulated and
    sent back as part of the tool interaction history.

    Args:
        interrupt: The original ToolRequest Part or ToolRequestPart that was interrupted.
        response_data: The data to include in the ToolResponse output. Defaults to None.
        metadata: Optional metadata to include in the resulting Part, often used
                  to signal that this response corresponds to an interrupt.
                  Defaults to {'interruptResponse': True}.

    Returns:
        A Part object containing the constructed ToolResponse.
    """
    # TODO: validate against tool schema
    tool_request = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request
    return Part(
        tool_response=ToolResponse(
            name=tool_request.name,
            ref=tool_request.ref,
            output=response_data,
        ),
        metadata={
            'interruptResponse': metadata if metadata else True,
        },
    )
