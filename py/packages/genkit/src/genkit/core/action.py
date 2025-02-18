# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.

import inspect
import json
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from genkit.core.tracing import tracer
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ActionKind(StrEnum):
    """Enumerates all the types of action that can be registered."""

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
    """The response from an action."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    response: Any
    trace_id: str = Field(alias='traceId')


class ActionMetadataKey(StrEnum):
    """Enumerates all the keys of the action metadata."""

    INPUT_KEY = 'inputSchema'
    OUTPUT_KEY = 'outputSchema'
    RETURN = 'return'


class ActionExecutionContext(BaseModel):
    """The context to the action callback."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)


def parse_action_key(key: str) -> tuple[ActionKind, str]:
    """Parse an action key into its kind and name components.

    The key format is `<kind>/<name>`.  Examples include:
    - `prompt/my-prompt`
    - `model/gpt-4`.

    Args:
        key: The action key to parse.

    Returns:
        A tuple of (kind, name).

    Raises:
        ValueError: If the key format is invalid or if the kind is not a valid ActionKind.
    """
    tokens = key.split('/')
    if len(tokens) != 2 or not tokens[0] or not tokens[1]:
        msg = (
            f'Invalid action key format: `{key}`. '
            'Expected format: `<kind>/<name>`'
        )
        raise ValueError(msg)

    kind_str, name = tokens
    try:
        kind = ActionKind(kind_str)
    except ValueError as e:
        msg = f'Invalid action kind: `{kind_str}`'
        raise ValueError(msg) from e
    return kind, name


class Action:
    """An action is a Typed JSON-based RPC-over-HTTP remote-callable function
    that supports metadata, streaming, reflection and discovery.

    It is strongly-typed, named, observable, uninterrupted operation that can be
    in streaming or non-streaming mode. It wraps a function that takes an input,
    and returns an output, optionally streaming values incrementally by invoking
    a streaming callback.

    An action can be registered in the registry and then be used in a flow.
    It can be of different kinds as defined by the ActionKind enum.
    """

    def __init__(
        self,
        kind: ActionKind,
        name: str,
        fn: Callable,
        description: str | None = None,
        metadata: dict[ActionMetadataKey, Any] | None = None,
        span_metadata: dict[str, str] | None = None,
        fn_context: ActionExecutionContext | None = None,
    ):
        """Initialize an action.

        Args:
            kind: The kind of the action.
            name: The name of the action.
            fn: The function to call when the action is executed.
            description: The description of the action.
            metadata: The metadata of the action.
            span_metadata: The span metadata of the action.
        """
        # TODO(Tatsiana Havina): separate a long constructor into methods.
        self.kind: ActionKind = kind
        self.name = name
        self.fn_context = fn_context

        def tracing_wrapper(*args, **kwargs):
            """Wraps the callable function in a tracing span and adds metadata
            to it."""

            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                span.set_attribute('genkit:type', kind)
                span.set_attribute('genkit:name', name)

                if span_metadata is not None:
                    for meta_key in span_metadata:
                        span.set_attribute(meta_key, span_metadata[meta_key])

                if len(args) > 0:
                    if isinstance(args[0], BaseModel):
                        encoded = args[0].model_dump_json(by_alias=True)
                        span.set_attribute('genkit:input', encoded)
                    else:
                        span.set_attribute('genkit:input', json.dumps(args[0]))

                if self.fn_context is not None:
                    if not isinstance(fn_context, ActionExecutionContext):
                        raise TypeError(
                            'Action Execution context must be of type '
                            "'ActionExecutionContext'"
                        )
                    kwargs['context'] = self.fn_context

                output = fn(*args, **kwargs)

                span.set_attribute('genkit:state', 'success')

                if isinstance(output, BaseModel):
                    encoded = output.model_dump_json(by_alias=True)
                    span.set_attribute('genkit:output', encoded)
                else:
                    span.set_attribute('genkit:output', json.dumps(output))

                return ActionResponse(response=output, trace_id=trace_id)

        self.fn = tracing_wrapper
        self.description = description
        self.metadata = metadata if metadata else {}

        input_spec = inspect.getfullargspec(fn)
        action_args = [
            k for k in input_spec.annotations if k != ActionMetadataKey.RETURN
        ]

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
