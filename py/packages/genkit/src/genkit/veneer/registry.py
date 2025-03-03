# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""This is the user facing Genkit registry API with methods to register models, flow, etc."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from genkit.ai.embedding import EmbedderFn
from genkit.ai.formats.types import FormatDef
from genkit.ai.model import ModelFn
from genkit.core.action import Action, ActionKind
from genkit.core.codec import dump_dict
from genkit.core.registry import Registry
from genkit.core.schema import to_json_schema
from genkit.core.typing import ModelInfo
from pydantic import BaseModel


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
            """Register the decorated function as a flow.

            Args:
                func: The function to register as a flow.

            Returns:
                The wrapped function that executes the flow.
            """
            flow_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=flow_name,
                kind=ActionKind.FLOW,
                fn=func,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
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
            """Register the decorated function as a tool.

            Args:
                func: The function to register as a tool.

            Returns:
                The wrapped function that executes the tool.
            """
            tool_name = name if name is not None else func.__name__
            action = self.registry.register_action(
                name=tool_name,
                kind=ActionKind.TOOL,
                description=description,
                fn=func,
            )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Asynchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return (await action.arun(*args, **kwargs)).response

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """Synchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return action.run(*args, **kwargs).response

            return async_wrapper if action.is_async else sync_wrapper

        return wrapper

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        config_schema: BaseModel | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        info: ModelInfo | None = None,
    ) -> Action:
        """Define a custom model action.
        Args:
            name: Name of the model.
            fn: Function implementing the model behavior.
            config_schema: Optional schema for model configuration.
            metadata: Optional metadata for the model.
            info: Optional ModelInfo for the model.
        """
        model_meta = metadata if metadata else {}
        if info:
            model_meta['model'] = dump_dict(info)
        if 'model' not in model_meta:
            model_meta['model'] = {}
        if (
            'label' not in model_meta['model']
            or not model_meta['model']['label']
        ):
            model_meta['model']['label'] = name

        if config_schema:
            model_meta['model']['customOptions'] = to_json_schema(config_schema)

        return self.registry.register_action(
            name=name,
            kind=ActionKind.MODEL,
            fn=fn,
            metadata=model_meta,
        )

    def define_embedder(
        self,
        name: str,
        fn: EmbedderFn,
        metadata: dict[str, Any] | None = None,
    ) -> Action:
        """Define a custom embedder action.
        Args:
            name: Name of the model.
            fn: Function implementing the embedder behavior.
            metadata: Optional metadata for the model.
        """
        return self.registry.register_action(
            name=name,
            kind=ActionKind.EMBEDDER,
            fn=fn,
            metadata=metadata,
        )

    def define_format(self, format: FormatDef):
        """Registers a custom format in the registry."""
        self.registry.register_value('format', format.name, format)
