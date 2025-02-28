# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from functools import wraps
from typing import Any

from genkit.ai.model import ModelFn
from genkit.core.action import Action, ActionKind
from genkit.core.registry import Registry


class GenkitRegistry:
    """User-facing API for interacting with Genkit registry."""

    def __init__(self):
        self.registry = Registry()

    def flow(self, name: str | None = None) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a flow.
        Args:
            name: Optional name for the flow. If not provided, uses the
                function name.
        Returns:
            A decorator function that registers the flow.
        """

        def wrapper(func: Callable) -> Callable:
            flow_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=flow_name,
                kind=ActionKind.FLOW,
                fn=func,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return action.run(*args, **kwargs).response

            return async_wrapper if action.is_async else sync_wrapper

        return wrapper

    def tool(
        self, description: str, name: str | None = None
    ) -> Callable[[Callable], Callable]:
        """Decorator to register a function as a tool.
        Args:
            description: Description for the tool to be passed to the model.
            name: Optional name for the flow. If not provided, uses the function name.
        Returns:
            A decorator function that registers the tool.
        """

        def wrapper(func: Callable) -> Callable:
            tool_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=tool_name,
                kind=ActionKind.TOOL,
                description=description,
                fn=func,
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return action.run(*args, **kwargs).response

            return async_wrapper if action.is_async else sync_wrapper

        return wrapper

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        metadata: dict[str, Any] | None = None,
    ) -> Action:
        """Define a custom model action.
        Args:
            name: Name of the model.
            fn: Function implementing the model behavior.
            metadata: Optional metadata for the model.
        """
        return self.registry.register_action(
            name=name,
            kind=ActionKind.MODEL,
            fn=fn,
            metadata=metadata,
        )
