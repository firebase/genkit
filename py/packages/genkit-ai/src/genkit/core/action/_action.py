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
    """Provides context for an action's execution, including streaming support.

    This class holds context information relevant to a single execution of an
    Action. It manages the streaming callback (`on_chunk`) and any additional
    context dictionary provided during the action call.

    Attributes:
        context: A dictionary containing arbitrary context data.
    """

    def __init__(
        self,
        on_chunk: StreamingCallback | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initializes an ActionRunContext instance.

        Sets up the context with an optional streaming callback and an optional
        context dictionary. If `on_chunk` is None, a no-op callback is used.

        Args:
            on_chunk: A callable to be invoked when a chunk of data is ready
                      during streaming execution. Defaults to a no-op function.
            context: An optional dictionary containing context data to be made
                     available within the action execution. Defaults to an empty
                     dictionary.
        """
        self._on_chunk = on_chunk if on_chunk is not None else noop_streaming_callback
        self.context = context if context is not None else {}

    @cached_property
    def is_streaming(self) -> bool:
        """Indicates whether the action is being executed in streaming mode.

        This property checks if a valid streaming callback (`on_chunk`)
        was provided during initialization.

        Returns:
            True if a streaming callback (other than the no-op default) is set,
            False otherwise.
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
    """Represents a strongly-typed, remotely callable function within Genkit.

    Actions are the fundamental building blocks for defining operations in Genkit.
    They are named, observable (via tracing), and support both streaming and
    non-streaming execution modes. An Action wraps a Python function, handling
    input validation, execution, tracing, and output serialization.

    Attributes:
        kind: The type category of the action (e.g., MODEL, TOOL, FLOW).
        name: A unique identifier for the action.
        description: An optional human-readable description.
        metadata: A dictionary for storing arbitrary metadata associated with the action.
        input_schema: The JSON schema definition for the expected input type.
        output_schema: The JSON schema definition for the expected output type.
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
        """Executes the action synchronously with the given input.

        This method runs the action's underlying function synchronously.
        It handles input validation, tracing, and output serialization.
        If the action's function is async, it will be run in the current event loop.

        Args:
            input: The input data for the action. It should conform to the action's
                   input schema.
            on_chunk: An optional callback function to receive streaming output chunks.
                      Note: For synchronous execution of streaming actions, chunks
                      will be delivered synchronously via this callback.
            context: An optional dictionary containing context data for the execution.
            telemetry_labels: Optional labels for telemetry.

        Returns:
            An ActionResponse object containing the final result and trace ID.

        Raises:
            GenkitError: If an error occurs during action execution.
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
        """Executes the action asynchronously with the given input.

        This method runs the action's underlying function asynchronously.
        It handles input validation, tracing, and output serialization.
        If the action's function is synchronous, it will be wrapped to run
        asynchronously.

        Args:
            input: The input data for the action. It should conform to the action's
                   input schema.
            on_chunk: An optional callback function to receive streaming output chunks.
            context: An optional dictionary containing context data for the execution.
            telemetry_labels: Optional labels for telemetry.

        Returns:
            An awaitable ActionResponse object containing the final result and trace ID.

        Raises:
            GenkitError: If an error occurs during action execution.
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
        """Executes the action asynchronously with raw, unvalidated input.

        This method bypasses the Pydantic input validation and calls the underlying
        action function directly with the provided `raw_input`. It still handles
        tracing and context management.

        Use this method when you need to work with input that may not conform
        to the defined schema or when you have already validated the input.

        Args:
            raw_input: The raw input data to pass directly to the action function.
            on_chunk: An optional callback function to receive streaming output chunks.
            context: An optional dictionary containing context data for the execution.
            telemetry_labels: Optional labels for telemetry.

        Returns:
            An awaitable ActionResponse object containing the final result and trace ID.

        Raises:
            GenkitError: If an error occurs during action execution.
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
        AsyncIterator,
        asyncio.Future[ActionResponse],
    ]:
        """Executes the action asynchronously and provides a streaming response.

        This method initiates an asynchronous action execution and returns immediately
        with a tuple containing an async iterator for the chunks and a future for the
        final response.

        Args:
            input: The input data for the action. It should conform to the action's
                   input schema.
            context: An optional dictionary containing context data for the execution.
            telemetry_labels: Optional labels for telemetry.

        Returns:
            A tuple: (chunk_iterator, final_response_future)
            - chunk_iterator: An AsyncIterator yielding output chunks as they become available.
            - final_response_future: An asyncio.Future that will resolve to the
                                     complete ActionResponse when the action finishes.
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
