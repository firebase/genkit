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

"""Tool-specific types and utilities for the Genkit framework.

Genkit tools are actions that can be called by models during a generation
process. This module provides context and error types for tool execution,
including support for controlled interruptions and specific response formatting.

Overview:
    Tools extend the capabilities of AI models by allowing them to call
    external functions during generation. The model decides when to use
    a tool based on the conversation context and tool descriptions.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Tool Execution Flow                                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐    │
    │  │  Model   │ ───► │   Tool   │ ───► │ Execute  │ ───► │  Model   │    │
    │  │ Request  │      │ Request  │      │ Function │      │ Continue │    │
    │  └──────────┘      └──────────┘      └──────────┘      └──────────┘    │
    │                          │                                             │
    │                          ▼ (if interrupt=True)                         │
    │                    ┌──────────┐                                        │
    │                    │  Pause   │ ────► User confirms ────► Resume       │
    │                    └──────────┘                                        │
    └─────────────────────────────────────────────────────────────────────────┘

Terminology:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Term                │ Description                                       │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ Tool                │ A function that models can call during generation │
    │ ToolRunContext      │ Execution context with interrupt capability       │
    │ ToolInterruptError  │ Exception for controlled tool execution pause     │
    │ Interrupt           │ A tool marked to pause for user confirmation      │
    │ tool_response()     │ Helper to construct response for interrupted tool │
    └─────────────────────┴───────────────────────────────────────────────────┘

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component           │ Purpose                                           │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ ToolRunContext      │ Context for tool execution, extends ActionContext │
    │ ToolInterruptError  │ Exception to pause execution for user input       │
    │ tool_response()     │ Constructs tool response Part for interrupts      │
    └─────────────────────┴───────────────────────────────────────────────────┘

Example:
    Basic tool definition:

    ```python
    from genkit import Genkit

    ai = Genkit()


    @ai.tool()
    def get_weather(city: str) -> str:
        '''Get current weather for a city.'''
        # Fetch weather data...
        return f'Weather in {city}: Sunny, 72°F'


    # Use in generation
    response = await ai.generate(
        prompt='What is the weather in Paris?',
        tools=['get_weather'],
    )
    ```

    Interrupt tool (human-in-the-loop):

    ```python
    @ai.tool(interrupt=True)
    def book_flight(destination: str, date: str) -> str:
        '''Book a flight - requires user confirmation.'''
        return f'Booked flight to {destination} on {date}'


    # First generate - tool call is returned, not executed
    response = await ai.generate(
        prompt='Book me a flight to Paris next Friday',
        tools=['book_flight'],
    )

    # Check for interrupts
    if response.interrupts:
        interrupt = response.interrupts[0]
        # Show user: "Confirm booking to Paris on Friday?"
        # Resume after confirmation
        response = await ai.generate(
            prompt='Book me a flight to Paris next Friday',
            tools=['book_flight'],
            messages=response.messages,
            resume={'respond': tool_response(interrupt, 'Confirmed')},
        )
    ```

Caveats:
    - Tools receive a ToolRunContext, which extends ActionRunContext
    - Interrupt tools must be explicitly resumed to continue generation
    - The tool_response() helper is used to respond to interrupted tools

See Also:
    - Interrupts documentation: https://genkit.dev/docs/tool-calling#pause-agentic-loops-with-interrupts
    - genkit.core.action: Base action types
"""

from typing import Any, NoReturn, Protocol, cast

from genkit.core.action import ActionRunContext
from genkit.core.typing import Metadata, Part, ToolRequestPart, ToolResponse, ToolResponsePart


class ToolRequestLike(Protocol):
    """Protocol for objects that look like a ToolRequest."""

    name: str
    ref: str | None


class ToolRunContext(ActionRunContext):
    """Provides context specific to the execution of a Genkit tool.

    Inherits from ActionRunContext and adds functionality relevant to tools,
    such as interrupting the tool's execution flow.
    """

    def __init__(
        self,
        ctx: ActionRunContext,
    ) -> None:
        """Initializes the ToolRunContext.

        Args:
            ctx: The parent ActionRunContext.
        """
        super().__init__(
            on_chunk=ctx._on_chunk if ctx.is_streaming else None,
            context=ctx.context,
        )

    def interrupt(self, metadata: dict[str, Any] | None = None) -> NoReturn:
        """Interrupts the current tool execution.

        Raises a ToolInterruptError, which can be caught by the generation
        process to handle controlled interruptions (e.g., asking the user for
        clarification).

        Args:
            metadata: Optional metadata to associate with the interrupt.
        """
        raise ToolInterruptError(metadata=metadata)


# TODO(#4346): make this extend GenkitError once it has INTERRUPTED status
class ToolInterruptError(Exception):
    """Exception raised to signal a controlled interruption of tool execution.

    This is used as a flow control mechanism within the generation process,
    allowing a tool to pause execution and potentially signal back to the
    calling flow (e.g., to request user input or clarification) without
    causing a hard failure.
    """

    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        """Initializes the ToolInterruptError.

        Args:
            metadata: Metadata associated with the interruption.
        """
        super().__init__()
        self.metadata: dict[str, Any] = metadata or {}


def tool_response(
    interrupt: Part | ToolRequestPart,
    response_data: object | None = None,
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
    # TODO(#4347): validate against tool schema
    tool_request = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request

    interrupt_metadata = True
    if isinstance(metadata, Metadata):
        interrupt_metadata = metadata.root
    elif metadata:
        interrupt_metadata = metadata

    tr = cast(ToolRequestLike, tool_request)
    return Part(
        root=ToolResponsePart(
            tool_response=ToolResponse(
                name=tr.name,
                ref=tr.ref,
                output=response_data,
            ),
            metadata=Metadata(
                root={
                    'interruptResponse': interrupt_metadata,
                }
            ),
        )
    )
