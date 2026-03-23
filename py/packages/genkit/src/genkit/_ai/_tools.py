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
from contextvars import ContextVar
from functools import wraps
from typing import Any, NoReturn, ParamSpec, TypeVar, cast

from genkit._core._action import ActionKind, ActionRunContext
from genkit._core._registry import Registry
from genkit._core._typing import Part, ToolRequest, ToolRequestPart, ToolResponse, ToolResponsePart

P = ParamSpec('P')
T = TypeVar('T')

# Context variables for propagating resumed metadata to tools
_tool_resumed_metadata: ContextVar[dict[str, Any] | None] = ContextVar('tool_resumed_metadata', default=None)
_tool_original_input: ContextVar[Any | None] = ContextVar('tool_original_input', default=None)


class ToolRunContext(ActionRunContext):
    """Tool execution context with interrupt support."""

    def __init__(
        self,
        ctx: ActionRunContext,
        resumed_metadata: dict[str, Any] | None = None,
        original_input: Any = None,
    ) -> None:
        """Initialize from parent ActionRunContext.

        Args:
            ctx: Parent action context
            resumed_metadata: Metadata from previous interrupt (if resumed)
            original_input: Original tool input before replacement (if resumed)
        """
        super().__init__(context=ctx.context)
        self.resumed_metadata = resumed_metadata
        self.original_input = original_input

    def interrupt(self, metadata: dict[str, Any] | None = None) -> NoReturn:
        """Raise ToolInterruptError to pause execution (e.g., for user input)."""
        raise ToolInterruptError(metadata=metadata)

    def is_resumed(self) -> bool:
        """Return True if this execution is resuming after an interrupt."""
        return self.resumed_metadata is not None


# TODO(#4346): make this extend GenkitError once it has INTERRUPTED status
class ToolInterruptError(Exception):
    """Controlled interruption of tool execution (e.g., to request user input)."""

    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        """Initialize with optional interrupt metadata."""
        super().__init__()
        self.metadata: dict[str, Any] = metadata or {}


class Interrupt(Exception):
    """Exception for interrupting tool execution with user-facing API.

    This is the public API for tool interrupts. Prefer using this over ToolInterruptError.
    Use raise Interrupt(data) inside a tool to pause execution.
    Use tool.respond(interrupt_part, output) or tool.restart(interrupt_part) to resume.
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an Interrupt exception.

        Args:
            data: Metadata to attach to the interrupt
            _interrupt_part: Internal - the Part containing the interrupted ToolRequestPart
            _registry: Internal - registry for tool schema validation
        """
        super().__init__()
        self.data = data or {}


def tool_response(
    interrupt: 'Part',
    output: Any,
    metadata: dict[str, Any] | None = None,
) -> 'Part':
    """Internal helper: construct a ToolResponsePart from an interrupted ToolRequestPart.

    Not exported on public API surface. Users should call tool.respond(interrupt_part, output).
    """
    from genkit._core._typing import Part as _Part, ToolResponse, ToolResponsePart

    interrupt_metadata = metadata if metadata is not None else True
    tool_req = interrupt.root.tool_request
    return _Part(
        root=ToolResponsePart(
            tool_response=ToolResponse(
                ref=tool_req.ref,
                name=tool_req.name,
                output=output,
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
        try:
            match len(input_spec.args):
                case 0:
                    return await func_any()
                case 1:
                    return await func_any(args[0])
                case 2:
                    # Read from context variables for resumed metadata
                    resumed_meta = _tool_resumed_metadata.get()
                    original_input = _tool_original_input.get()
                    return await func_any(
                        args[0],
                        ToolRunContext(
                            cast(ActionRunContext, args[1]),
                            resumed_metadata=resumed_meta,
                            original_input=original_input,
                        ),
                    )
                case _:
                    raise ValueError('tool must have 0-2 args...')
        except Interrupt as e:
            # Convert Interrupt to ToolInterruptError for compatibility with existing flow
            raise ToolInterruptError(metadata=e.data) from e

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

    # Add respond and restart methods to the wrapper
    def respond(
        interrupt: Part | ToolRequestPart,
        output_data: Any,  # noqa: ANN401
        metadata: dict[str, Any] | None = None,
    ) -> Part:
        """Create a tool response for an interrupted request.

        Args:
            interrupt: The interrupted tool request part
            output_data: The response data (validated against tool output schema)
            metadata: Optional metadata for the response

        Returns:
            Part with ToolResponsePart containing the response
        """
        # Validate it's the right tool
        tool_req = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request
        if tool_req.name != tool_name:
            raise ValueError(f"Interrupt is for tool '{tool_req.name}', not '{tool_name}'")

        # TODO(#4347): Get output schema from action and pass to tool_response for validation
        return tool_response(interrupt, output_data, metadata)

    def restart(
        interrupt: Part | ToolRequestPart,
        replace_input: Any | None = None,  # noqa: ANN401
        resumed_metadata: dict[str, Any] | None = None,
    ) -> Part:
        """Create a restart request for an interrupted tool call.

        Args:
            interrupt: The interrupted tool request part
            replace_input: Optional new input to replace the original
            resumed_metadata: Metadata passed to tool via ToolRunContext.resumed_metadata

        Returns:
            Part with modified ToolRequestPart for re-execution
        """
        # Validate it's the right tool
        tool_req = interrupt.root.tool_request if isinstance(interrupt, Part) else interrupt.tool_request
        if tool_req.name != tool_name:
            raise ValueError(f"Interrupt is for tool '{tool_req.name}', not '{tool_name}'")

        # Build new metadata - get from root.metadata for Part
        if isinstance(interrupt, Part):
            existing_meta = interrupt.root.metadata or {}
        else:
            existing_meta = interrupt.metadata or {}
        new_meta = dict(existing_meta) if existing_meta else {}

        # Mark as resumed
        new_meta['resumed'] = resumed_metadata if resumed_metadata is not None else True

        # Store original input if replacing
        new_input = tool_req.input
        if replace_input is not None:
            new_meta['replacedInput'] = tool_req.input
            new_input = replace_input

        # Remove interrupt marker
        if 'interrupt' in new_meta:
            del new_meta['interrupt']

        return Part(
            root=ToolRequestPart(
                tool_request=ToolRequest(
                    name=tool_req.name,
                    ref=tool_req.ref,
                    input=new_input,
                ),
                metadata=new_meta,
            )
        )

    wrapper.respond = respond  # type: ignore[attr-defined]
    wrapper.restart = restart  # type: ignore[attr-defined]

    return cast(Callable[P, T], wrapper)


def define_interrupt(
    registry: Registry,
    func: Callable[P, T] | None,
    name: str | None = None,
    description: str | None = None,
    request_metadata: dict[str, Any] | Callable[[Any], dict[str, Any]] | None = None,
) -> Callable[P, T]:
    """Register a tool that always interrupts execution.

    An interrupt tool is a special tool that always calls ctx.interrupt() with
    optional metadata. This is useful for explicit human-in-the-loop checkpoints.

    Args:
        registry: The registry to register the interrupt tool in
        func: Optional tool function. If None, immediately interrupts with request_metadata
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        request_metadata: Static metadata dict or function(input) -> dict for the interrupt

    Returns:
        The registered tool function

    Example:
        # Simple interrupt that always pauses for confirmation
        @define_interrupt(registry, description="Ask user for confirmation")
        async def confirm_action(input: dict, ctx: ToolRunContext) -> dict:
            # This never executes during initial call - always interrupts
            return {"confirmed": True}

        # Interrupt with custom metadata
        def get_meta(input: dict) -> dict:
            return {"action": input.get("action"), "requires_approval": True}

        confirm = define_interrupt(
            registry,
            None,
            name="confirm",
            description="Requires user approval",
            request_metadata=get_meta
        )
    """

    async def interrupt_wrapper(input: Any, ctx: ToolRunContext) -> Any:  # noqa: ANN401
        meta = None
        if callable(request_metadata):
            meta = request_metadata(input)
        elif request_metadata is not None:
            meta = request_metadata
        ctx.interrupt(metadata=meta)
        # Type checkers will complain here, but this never returns
        raise AssertionError('Unreachable')  # type: ignore[unreachable]

    return define_tool(
        registry,
        interrupt_wrapper if func is None else func,
        name=name,
        description=description,
    )
