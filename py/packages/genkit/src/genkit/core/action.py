# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import inspect
import json

from typing import Dict, Optional, Callable, Any
from pydantic import ConfigDict, BaseModel, TypeAdapter

from genkit.core.tracing import tracer


class ActionResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    response: Any
    traceId: str


class Action:

    INPUT_KEY = 'inputSchema'
    OUTPUT_KEY = 'outputSchema'

    def __init__(
        self,
        action_type: str,
        name: str,
        fn: Callable,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        span_metadata: Optional[Dict[str, str]] = None,
    ):
        # TODO(Tatsiana Havina): separate a long constructor into methods.
        self.type = action_type
        self.name = name

        def fn_to_call(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                trace_id = str(span.get_span_context().trace_id)
                span.set_attribute('genkit:type', action_type)
                span.set_attribute('genkit:name', name)

                if span_metadata is not None:
                    for meta_key in span_metadata:
                        span.set_attribute(meta_key, span_metadata[meta_key])

                if len(args) > 0:
                    if isinstance(args[0], BaseModel):
                        span.set_attribute('genkit:input', args[0].model_dump_json())
                    else:
                        span.set_attribute('genkit:input', json.dumps(args[0]))

                output = fn(*args, **kwargs)

                span.set_attribute('genkit:state', 'success')

                if isinstance(output, BaseModel):
                    span.set_attribute('genkit:output', output.model_dump_json())
                else:
                    span.set_attribute('genkit:output', json.dumps(output))

                return ActionResponse(response=output, traceId=trace_id)

        self.fn = fn_to_call
        self.description = description
        self.metadata = metadata if metadata else {}

        input_spec = inspect.getfullargspec(fn)
        action_args = [k for k in input_spec.annotations if k != 'return']
        if len(action_args) > 1:
            raise Exception('can only have one arg')
        if len(action_args) > 0:
            type_adapter = TypeAdapter(input_spec.annotations[action_args[0]])
            self.input_schema = type_adapter.json_schema()
            self.input_type = type_adapter
            self.metadata[self.INPUT_KEY] = self.input_schema
        else:
            self.input_schema = TypeAdapter(Any).json_schema()
            self.metadata[self.INPUT_KEY] = self.input_schema

        if 'return' in input_spec.annotations:
            type_adapter = TypeAdapter(input_spec.annotations['return'])
            self.output_schema = type_adapter.json_schema()
            self.metadata[self.OUTPUT_KEY] = self.output_schema
        else:
            self.output_schema = TypeAdapter(Any).json_schema()
            self.metadata[self.OUTPUT_KEY] = self.output_schema
