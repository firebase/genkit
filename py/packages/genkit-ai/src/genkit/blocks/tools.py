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
from genkit.typing import Part, ToolRequestPart, ToolResponse


class ToolRunContext(ActionRunContext):
    """Context for an tool execution."""

    def __init__(
        self,
        ctx: ActionRunContext,
    ):
        super().__init__(
            on_chunk=ctx._on_chunk if ctx.is_streaming else None,
            context=ctx.context,
        )

    def interrupt(self, metadata: dict[str, Any] | None = None):
        """Interrupts current execution of the tool."""
        raise ToolInterruptError(metadata=metadata)


# TODO: make this extend GenkitError once it has INTERRUPTED status
class ToolInterruptError(Exception):
    """Error throw to interrupt tool execution. Used for tool flow control."""

    def __init__(self, metadata: dict[str, Any]):
        self.metadata = metadata


def tool_response(
    interrupt: Part | ToolRequestPart,
    responseData: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> Part:
    """Constructs a tool response for an interrupted request."""
    # TODO: validate against tool schema
    tool_request = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request
    return Part(
        tool_response=ToolResponse(
            name=tool_request.name,
            ref=tool_request.ref,
            output=responseData,
        ),
        metadata={
            'interruptResponse': metadata if metadata else True,
        },
    )
