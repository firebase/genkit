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

"""Tool-specific types and utilities for the Genkit framework."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, NoReturn, ParamSpec, TypeVar, cast

from genkit._core._action import ActionKind, ActionRunContext
from genkit._core._registry import Registry
from genkit._core._typing import Part, ToolRequest, ToolRequestPart, ToolResponse, ToolResponsePart

P = ParamSpec('P')
T = TypeVar('T')


class ToolRunContext(ActionRunContext):
    """Tool execution context with interrupt support."""

    def __init__(
        self,
        ctx: ActionRunContext,
    ) -> None:
        """Initialize from parent ActionRunContext."""
        super().__init__(context=ctx.context)

    def interrupt(self, metadata: dict[str, Any] | None = None) -> NoReturn:
        """Raise ToolInterruptError to pause execution (e.g., for user input)."""
        raise ToolInterruptError(metadata=metadata)


# TODO(#4346): make this extend GenkitError once it has INTERRUPTED status
class ToolInterruptError(Exception):
    """Controlled interruption of tool execution (e.g., to request user input)."""

    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        """Initialize with optional interrupt metadata."""
        super().__init__()
        self.metadata: dict[str, Any] = metadata or {}


def tool_response(
    interrupt: Part | ToolRequestPart,
    response_data: object | None = None,
    metadata: dict[str, Any] | None = None,
) -> Part:
    """Create a ToolResponse Part for an interrupted tool request."""
    # TODO(#4347): validate against tool schema
    tool_request = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request

    interrupt_metadata: dict[str, Any] | bool = True
    if isinstance(metadata, dict):
        interrupt_metadata = metadata
    elif metadata:
        interrupt_metadata = metadata

    tr = cast(ToolRequest, tool_request)
    return Part(
        root=ToolResponsePart(
            tool_response=ToolResponse(
                name=tr.name,
                ref=tr.ref,
                output=response_data,
            ),
            metadata={'interruptResponse': interrupt_metadata},
        )
    )


def _get_func_description(func: Callable[..., Any], description: str | None = None) -> str:
    """Return description if provided, otherwise use the function's docstring."""
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


def define_tool(
    registry: Registry,
    func: Callable[P, T],
    name: str | None = None,
    description: str | None = None,
) -> Callable[P, T]:
    """Register a function as a tool.

    Args:
        registry: The registry to register the tool in.
        func: The async function to register as a tool. Must be a coroutine function.
        name: Optional name for the tool. Defaults to the function name.
        description: Optional description. Defaults to the function's docstring.

    Raises:
        TypeError: If func is not an async function.
    """
    # All Python functions have __name__, but ty is strict about Callable protocol
    if not inspect.iscoroutinefunction(func):
        raise TypeError(f'Tool function must be async. Got sync function: {func.__name__}')  # ty: ignore[unresolved-attribute]

    tool_name = name if name is not None else getattr(func, '__name__', 'unnamed_tool')
    tool_description = _get_func_description(func, description)

    input_spec = inspect.getfullargspec(func)

    func_any = cast(Callable[..., Any], func)

    async def tool_fn_wrapper(*args: Any) -> Any:  # noqa: ANN401
        # Dynamic dispatch based on function signature - pyright can't verify ParamSpec here
        match len(input_spec.args):
            case 0:
                return await func_any()
            case 1:
                return await func_any(args[0])
            case 2:
                return await func_any(args[0], ToolRunContext(cast(ActionRunContext, args[1])))
            case _:
                raise ValueError('tool must have 0-2 args...')

    action = registry.register_action(
        name=tool_name,
        kind=ActionKind.TOOL,
        description=tool_description,
        fn=tool_fn_wrapper,
        metadata_fn=func,
    )

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # noqa: ANN401
        action_any = cast(Any, action)
        return (await action_any.run(*args, **kwargs)).response

    return cast(Callable[P, T], wrapper)
