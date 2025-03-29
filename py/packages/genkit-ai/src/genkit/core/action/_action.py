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

"""Action module for defining and managing RPC-over-HTTP functions.

This module provides the core functionality for creating and managing actions in
the Genkit framework. Actions are strongly-typed, named, observable,
uninterrupted operations that can operate in streaming or non-streaming mode.
"""

import asyncio
import inspect
from collections.abc import AsyncIterator, Callable
from contextvars import ContextVar
from functools import cached_property
from typing import Any

from pydantic import TypeAdapter

from genkit.aio import Channel, ensure_async
from genkit.core.error import GenkitError
from genkit.core.tracing import tracer

from ._tracing import record_input_metadata, record_output_metadata
from ._util import extract_action_args_and_types, noop_streaming_callback
from .types import ActionKind, ActionMetadataKey, ActionResponse

# TODO: add typing, generics
StreamingCallback = Callable[[Any], None]


_action_context: ContextVar[dict[str, Any] | None] = ContextVar('context')
_action_context.set(None)


class ActionRunContext:
    """Context for an action execution."""

    def __init__(
        self,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize an ActionRunContext.

        Args:
            on_chunk: The callback to invoke when a chunk is received.
            context: The context to pass to the action.
        """
        self._on_chunk = on_chunk if on_chunk is not None else noop_streaming_callback
        self.context = context if context is not None else {}

    @cached_property
    def is_streaming(self) -> bool:
        """Determines whether context contains on chunk callback.

        Returns:
            Boolean indicating whether the context contains a streaming
            callback.
        """
        return self._on_chunk != noop_streaming_callback

    def send_chunk(self, chunk: Any) -> None:
        """Send a chunk to from the action to the client.

        Args:
            chunk: The chunk to send to the client.
        """
        self._on_chunk(chunk)

    @staticmethod
    def _current_context() -> dict[str, Any] | None:
        """Obtains current context if running within an action.

        Returns:
            The current context if running within an action, None otherwise.
        """
        return _action_context.get(None)


class Action:
    """An action is a Typed JSON-based RPC-over-HTTP remote-callable function.

    Actions support metadata, streaming, reflection and discovery. They are
    strongly-typed, named, observable, uninterrupted operations that can operate
    in streaming or non-streaming mode. An action wraps a function that takes an
    input and returns an output, optionally streaming values incrementally by
    invoking a streaming callback.
    """

    def __init__(
        self,
        kind: ActionKind,
        name: str,
        fn: Callable[..., Any],
        metadata_fn: Callable[..., Any] | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        span_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an Action.

        Args:
            kind: The kind of action (e.g., TOOL, MODEL, etc.).
            name: Unique name identifier for this action.
            fn: The function to call when the action is executed.
            metadata_fn: The function to be used to infer metadata (e.g.
                schemas).
            description: Optional human-readable description of the action.
            metadata: Optional dictionary of metadata about the action.
            span_metadata: Optional dictionary of tracing span metadata.
        """
        self.kind = kind
        self.name = name

        input_spec = inspect.getfullargspec(metadata_fn if metadata_fn else fn)
        action_args, arg_types = extract_action_args_and_types(input_spec)

        afn = ensure_async(fn)
        self.is_async = asyncio.iscoroutinefunction(fn)

        async def async_tracing_wrapper(input: Any | None, ctx: ActionRunContext) -> ActionResponse:
            """Wrap the function in an async tracing wrapper.

            Args:
                input: The input to the action.
                ctx: The context to pass to the action.

            Returns:
                The action response.
            """
            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                record_input_metadata(
                    span=span,
                    kind=kind,
                    name=name,
                    span_metadata=span_metadata,
                    input=input,
                )

                try:
                    match len(action_args):
                        case 0:
                            output = await afn()
                        case 1:
                            output = await afn(input)
                        case 2:
                            output = await afn(input, ctx)
                        case _:
                            raise ValueError('action fn must have 0-2 args...')
                except Exception as e:
                    raise GenkitError(
                        cause=e.cause if isinstance(e, GenkitError) and e.cause else e,
                        message=f'Error while running action {self.name}',
                        trace_id=trace_id,
                    )

                record_output_metadata(span, output=output)
                return ActionResponse(response=output, trace_id=trace_id)

        def sync_tracing_wrapper(input: Any | None, ctx: ActionRunContext) -> ActionResponse:
            """Wrap the function in a sync tracing wrapper.

            Args:
                input: The input to the action.
                ctx: The context to pass to the action.

            Returns:
                The action response.
            """
            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                record_input_metadata(
                    span=span,
                    kind=kind,
                    name=name,
                    span_metadata=span_metadata,
                    input=input,
                )

                try:
                    match len(action_args):
                        case 0:
                            output = fn()
                        case 1:
                            output = fn(input)
                        case 2:
                            output = fn(input, ctx)
                        case _:
                            raise ValueError('action fn must have 0-2 args...')
                except Exception as e:
                    raise GenkitError(
                        cause=e,
                        message=f'Error while running action {self.name}',
                        trace_id=trace_id,
                    )

                record_output_metadata(span, output=output)
                return ActionResponse(response=output, trace_id=trace_id)

        self.__fn = sync_tracing_wrapper
        self.__afn = async_tracing_wrapper
        self.description = description
        self.metadata = metadata if metadata else {}

        if len(action_args) > 2:
            raise Exception(f'can only have up to 2 arg: {action_args}')
        if len(action_args) > 0:
            type_adapter = TypeAdapter(arg_types[0])
            self.input_schema = type_adapter.json_schema()
            self.input_type = type_adapter
            self.metadata[ActionMetadataKey.INPUT_KEY] = self.input_schema
        else:
            self.input_schema = TypeAdapter(Any).json_schema()
            self.input_type = None
            self.metadata[ActionMetadataKey.INPUT_KEY] = self.input_schema

        if ActionMetadataKey.RETURN in input_spec.annotations:
            type_adapter = TypeAdapter(input_spec.annotations[ActionMetadataKey.RETURN])
            self.output_schema = type_adapter.json_schema()
            self.metadata[ActionMetadataKey.OUTPUT_KEY] = self.output_schema
        else:
            self.output_schema = TypeAdapter(Any).json_schema()
            self.metadata[ActionMetadataKey.OUTPUT_KEY] = self.output_schema

    def run(
        self,
        input: Any = None,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ) -> ActionResponse:
        """Run the action with input.

        Args:
            input: The input to the action.
            on_chunk: The callback to invoke when a chunk is received.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            The action response.
        """
        # TODO: handle telemetry_labels

        if context:
            _action_context.set(context)

        return self.__fn(
            input,
            ActionRunContext(on_chunk=on_chunk, context=_action_context.get(None)),
        )

    async def arun(
        self,
        input: Any = None,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ) -> ActionResponse:
        """Run the action with raw input.

        Args:
            input: The input to the action.
            on_chunk: The callback to invoke when a chunk is received.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            The action response.
        """
        # TODO: handle telemetry_labels

        if context:
            _action_context.set(context)

        return await self.__afn(
            input,
            ActionRunContext(on_chunk=on_chunk, context=_action_context.get(None)),
        )

    async def arun_raw(
        self,
        raw_input: Any,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ):
        """Run the action with raw input.

        Args:
            raw_input: The raw input to the action.
            on_chunk: The callback to invoke when a chunk is received.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            The action response.
        """
        input_action = self.input_type.validate_python(raw_input) if self.input_type is not None else None
        return await self.arun(
            input=input_action,
            on_chunk=on_chunk,
            context=context,
            telemetry_labels=telemetry_labels,
        )

    def stream(
        self,
        input: Any = None,
        context: dict[str, Any] | None = None,
        telemetry_labels: dict[str, Any] | None = None,
    ) -> tuple[
        AsyncIterator[ActionResponse],
        asyncio.Future[ActionResponse],
    ]:
        """Run the action and return an async iterator of the results.

        Args:
            input: The input to the action.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.

        Returns:
            A tuple containing:
            - An AsyncIterator of the chunks from the action.
            - An asyncio.Future that resolves to the final result of the action.
        """
        stream = Channel()

        resp = self.arun(
            input=input,
            context=context,
            telemetry_labels=telemetry_labels,
            on_chunk=lambda c: stream.send(c),
        )
        stream.set_close_future(resp)

        result_future: asyncio.Future[ActionResponse] = asyncio.Future()
        stream.closed.add_done_callback(lambda _: result_future.set_result(stream.closed.result().response))

        return (stream, result_future)
