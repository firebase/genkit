# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Action module for defining and managing RPC-over-HTTP functions.

This module provides the core functionality for creating and managing actions in
the Genkit framework. Actions are strongly-typed, named, observable,
uninterrupted operations that can operate in streaming or non-streaming mode.
"""

import asyncio
import inspect
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from genkit.core.tracing import tracer
from genkit.core.utils import dump_json
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

# TODO: add typing, generics
StreamingCallback = Callable[[Any], None]


class ActionKind(StrEnum):
    """Enumerates all the types of action that can be registered.

    This enum defines the various types of actions supported by the framework,
    including chat models, embedders, evaluators, and other utility functions.
    """

    CHATLLM = 'chat-llm'
    CUSTOM = 'custom'
    EMBEDDER = 'embedder'
    EVALUATOR = 'evaluator'
    FLOW = 'flow'
    INDEXER = 'indexer'
    MODEL = 'model'
    PROMPT = 'prompt'
    RETRIEVER = 'retriever'
    TEXTLLM = 'text-llm'
    TOOL = 'tool'
    UTIL = 'util'


class ActionResponse(BaseModel):
    """The response from an action.

    Attributes:
        response: The actual response data from the action execution.
        trace_id: A unique identifier for tracing the action execution.
    """

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    response: Any
    trace_id: str = Field(alias='traceId')


class ActionMetadataKey(StrEnum):
    """Enumerates all the keys of the action metadata.

    Attributes:
        INPUT_KEY: Key for the input schema metadata.
        OUTPUT_KEY: Key for the output schema metadata.
        RETURN: Key for the return type metadata.
    """

    INPUT_KEY = 'inputSchema'
    OUTPUT_KEY = 'outputSchema'
    RETURN = 'return'


def parse_action_key(key: str) -> tuple[ActionKind, str]:
    """Parse an action key into its kind and name components.

    Args:
        key: The action key to parse, in the format "kind/name".

    Returns:
        A tuple containing the ActionKind and name.

    Raises:
        ValueError: If the key format is invalid or if the kind is not a valid
            ActionKind.
    """
    tokens = key.split('/')
    if len(tokens) < 3 or not tokens[1] or not tokens[2]:
        msg = (
            f'Invalid action key format: `{key}`. Expected format: `<kind>/<n>`'
        )
        raise ValueError(msg)

    kind_str = tokens[1]
    name = tokens[2]
    try:
        kind = ActionKind(kind_str)
    except ValueError as e:
        msg = f'Invalid action kind: `{kind_str}`'
        raise ValueError(msg) from e
    return kind, name


def NOOP_STREAMING_CALLBACK(chunk: Any):
    pass


class ActionRunContext:
    def __init__(self, on_chunk: StreamingCallback = None, context: Any = None):
        self.__on_chunk = (
            on_chunk if on_chunk != None else NOOP_STREAMING_CALLBACK
        )
        self.context = context if context != None else {}

    def send_chunk(self, chunk: Any):
        self.__on_chunk(chunk)


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
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        span_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an Action.

        Args:
            kind: The kind of action (e.g., TOOL, MODEL, etc.).
            name: Unique name identifier for this action.
            fn: The function to call when the action is executed.
            description: Optional human-readable description of the action.
            metadata: Optional dictionary of metadata about the action.
            span_metadata: Optional dictionary of tracing span metadata.
        """
        self.kind = kind
        self.name = name

        input_spec = inspect.getfullargspec(fn)
        action_args = [
            k for k in input_spec.annotations if k != ActionMetadataKey.RETURN
        ]

        afn = ensure_async(fn)
        self.is_async = asyncio.iscoroutinefunction(fn)

        async def async_tracing_wrapper(
            input: Any | None, ctx: ActionRunContext
        ):
            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                record_input_metadata(
                    span=span,
                    kind=kind,
                    name=name,
                    span_metadata=span_metadata,
                    input=input,
                )

                match len(action_args):
                    case 0:
                        output = await afn()
                    case 1:
                        output = await afn(input)
                    case 2:
                        output = await afn(input, ctx)
                    case _:
                        raise ValueError('action fn must have 0-2 args...')

                record_output_metadata(span, output=output)
                return ActionResponse(response=output, trace_id=trace_id)

        def sync_tracing_wrapper(input: Any | None, ctx: ActionRunContext):
            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                record_input_metadata(
                    span=span,
                    kind=kind,
                    name=name,
                    span_metadata=span_metadata,
                    input=input,
                )

                match len(action_args):
                    case 0:
                        output = fn()
                    case 1:
                        output = fn(input)
                    case 2:
                        output = fn(input, ctx)
                    case _:
                        raise ValueError('action fn must have 0-2 args...')

                record_output_metadata(span, output=output)
                return ActionResponse(response=output, trace_id=trace_id)

        self.__fn = sync_tracing_wrapper
        self.__afn = async_tracing_wrapper
        self.description = description
        self.metadata = metadata if metadata else {}

        if len(action_args) > 2:
            raise Exception('can only have one arg')
        if len(action_args) > 0:
            type_adapter = TypeAdapter(input_spec.annotations[action_args[0]])
            self.input_schema = type_adapter.json_schema()
            self.input_type = type_adapter
            self.metadata[ActionMetadataKey.INPUT_KEY] = self.input_schema
        else:
            self.input_schema = TypeAdapter(Any).json_schema()
            self.metadata[ActionMetadataKey.INPUT_KEY] = self.input_schema

        if ActionMetadataKey.RETURN in input_spec.annotations:
            type_adapter = TypeAdapter(
                input_spec.annotations[ActionMetadataKey.RETURN]
            )
            self.output_schema = type_adapter.json_schema()
            self.metadata[ActionMetadataKey.OUTPUT_KEY] = self.output_schema
        else:
            self.output_schema = TypeAdapter(Any).json_schema()
            self.metadata[ActionMetadataKey.OUTPUT_KEY] = self.output_schema

    def run(
        self,
        input: Any = None,
        on_chunk: StreamingCallback = None,
        context: dict[str, Any] = None,
        telemetry_labels: dict[str, Any] = None,
    ) -> ActionResponse:
        # TODO: handle telemetry_labels
        # TODO: propagate context down the callstack via contextvars
        return self.__fn(
            input, ActionRunContext(on_chunk=on_chunk, context=context)
        )

    async def arun(
        self,
        input: Any = None,
        on_chunk: StreamingCallback = None,
        context: dict[str, Any] = None,
        telemetry_labels: dict[str, Any] = None,
    ) -> ActionResponse:
        # TODO: handle telemetry_labels
        # TODO: propagate context down the callstack via contextvars
        return await self.__afn(
            input, ActionRunContext(on_chunk=on_chunk, context=context)
        )

    async def arun_raw(
        self,
        raw_input: Any,
        on_chunk: StreamingCallback = None,
        context: dict[str, Any] = None,
        telemetry_labels: dict[str, Any] = None,
    ):
        input_action = self.input_type.validate_python(raw_input)
        return await self.arun(
            input=input_action,
            on_chunk=on_chunk,
            context=context,
            telemetry_labels=telemetry_labels,
        )


def record_input_metadata(span, kind, name, span_metadata, input):
    span.set_attribute('genkit:type', kind)
    span.set_attribute('genkit:name', name)

    if input != None:
        span.set_attribute('genkit:input', dump_json(input))

    if span_metadata is not None:
        for meta_key in span_metadata:
            span.set_attribute(meta_key, span_metadata[meta_key])


def record_output_metadata(span, output):
    span.set_attribute('genkit:state', 'success')
    span.set_attribute('genkit:output', dump_json(output))


def ensure_async(fn: Callable) -> Callable:
    is_async = asyncio.iscoroutinefunction(fn)
    if is_async:
        return fn

    async def asyn_wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return asyn_wrapper
