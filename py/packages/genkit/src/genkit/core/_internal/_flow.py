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

"""Flow wrapper and utilities for Genkit.

This module provides the FlowWrapper class that wraps flow functions to add
streaming capabilities via the `stream` method.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import wraps
from typing import Any, Generic, ParamSpec, cast

from typing_extensions import Never, TypeVar

from genkit.core.action import Action, ActionResponse
from genkit.core.action import ActionKind
from genkit.core._internal._registry import Registry

P = ParamSpec('P')
T = TypeVar('T')
CallT = TypeVar('CallT')
ChunkT = TypeVar('ChunkT', default=Never)


def get_func_description(func: Callable[..., Any], description: str | None = None) -> str:
    """Get the description of a function.

    Args:
        func: The function to get the description of.
        description: The description to use if the function docstring is
            empty.
    """
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


class FlowWrapper(Generic[P, CallT, T, ChunkT]):
    """A wrapper for flow functions to add `stream` method.

    This class wraps a flow function and provides a `stream` method for
    asynchronous execution.
    """

    def __init__(self, fn: Callable[P, CallT], action: Action[Any, T, ChunkT]) -> None:
        """Initialize the FlowWrapper.

        Args:
            fn: The function to wrap.
            action: The action to wrap.
        """
        self._fn: Callable[P, CallT] = fn
        self._action: Action[Any, T, ChunkT] = action

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> CallT:
        """Call the wrapped function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwds: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.
        """
        return self._fn(*args, **kwds)

    def stream(
        self,
        input: object = None,
        context: dict[str, object] | None = None,
        telemetry_labels: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> tuple[AsyncIterator[ChunkT], asyncio.Future[ActionResponse[T]]]:
        """Run the flow and return an async iterator of the results.

        Args:
            input: The input to the action.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.
            timeout: The timeout for the streaming action.

        Returns:
            A tuple containing:
            - An AsyncIterator of the chunks from the action.
            - An asyncio.Future that resolves to the final result of the action.
        """
        return self._action.stream(input=input, context=context, telemetry_labels=telemetry_labels, timeout=timeout)


def define_flow(
    registry: Registry,
    func: Callable[P, Awaitable[T]] | Callable[P, T],
    name: str | None = None,
    description: str | None = None,
) -> 'FlowWrapper[P, Awaitable[T] | T, T, Never]':
    """Register a function as a flow.

    Args:
        registry: The registry to register the flow in.
        func: The function to register as a flow.
        name: Optional name for the flow. If not provided, uses the
            function name.
        description: Optional description for the flow. If not provided,
            uses the function docstring.

    Returns:
        A FlowWrapper that can be called like the original function.
    """
    flow_name = name if name is not None else getattr(func, '__name__', 'unnamed_flow')
    flow_description = get_func_description(func, description)
    action = registry.register_action(
        name=flow_name,
        kind=cast(ActionKind, ActionKind.FLOW),
        # pyrefly: ignore[bad-argument-type] - func union type is valid for register_action
        fn=func,
        description=flow_description,
        span_metadata={'genkit:metadata:flow:name': flow_name},
    )

    # pyrefly: ignore[bad-argument-type] - func is valid for wraps despite union type
    @wraps(func)
    async def async_wrapper(*args: P.args, **_kwargs: P.kwargs) -> T:
        """Asynchronous wrapper for the flow function.

        Args:
            *args: Positional arguments to pass to the flow function.
            **_kwargs: Keyword arguments (unused, for signature compatibility).

        Returns:
            The response from the flow function.
        """
        # Flows accept at most one input argument
        input_arg = cast(T | None, args[0] if args else None)
        return (await action.run(input_arg)).response

    # pyrefly: ignore[bad-argument-type] - func is valid for wraps despite union type
    @wraps(func)
    def sync_wrapper(*args: P.args, **_kwargs: P.kwargs) -> T:
        """Synchronous wrapper for the flow function.

        Args:
            *args: Positional arguments to pass to the flow function.
            **_kwargs: Keyword arguments (unused, for signature compatibility).

        Returns:
            The response from the flow function.
        """
        # Flows accept at most one input argument
        input_arg = cast(T | None, args[0] if args else None)
        return action.run(input_arg).response

    wrapped_fn = cast(
        Callable[P, Awaitable[T]] | Callable[P, T], async_wrapper if action.is_async else sync_wrapper
    )
    flow = FlowWrapper(
        fn=cast(Callable[P, Awaitable[T] | T], wrapped_fn),
        action=cast(Action[Any, T, Never], action),
    )
    return flow
