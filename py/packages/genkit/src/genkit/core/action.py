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
    def __init__(
        self,
        type: str,
        name: str,
        fn: Callable,
        description: str | None = None,
        metadata: Optional[Dict[str, Any]] = None,
        spanMetadata: Optional[Dict[str, str]] = None,
    ):
        self.type = type
        self.name = name

        def fnToCall(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                traceId = str(span.get_span_context().trace_id)
                span.set_attribute('genkit:type', type)
                span.set_attribute('genkit:name', name)

                if spanMetadata is not None:
                    for spanMetaKey in spanMetadata:
                        span.set_attribute(
                            spanMetaKey, spanMetadata[spanMetaKey]
                        )

                if len(args) > 0:
                    if isinstance(args[0], BaseModel):
                        span.set_attribute(
                            'genkit:input', args[0].model_dump_json()
                        )
                    else:
                        span.set_attribute('genkit:input', json.dumps(args[0]))

                output = fn(*args, **kwargs)

                span.set_attribute('genkit:state', 'success')

                if isinstance(output, BaseModel):
                    span.set_attribute(
                        'genkit:output', output.model_dump_json()
                    )
                else:
                    span.set_attribute('genkit:output', json.dumps(output))

                return ActionResponse(response=output, traceId=traceId)

        self.fn = fnToCall
        self.description = description
        self.metadata = metadata
        if self.metadata is None:
            self.metadata = {}

        inputSpec = inspect.getfullargspec(fn)
        actionArgs = list(
            filter(lambda k: k != 'return', inputSpec.annotations)
        )
        if len(actionArgs) > 1:
            raise Exception('can only have one arg')
        if len(actionArgs) > 0:
            ta = TypeAdapter(inputSpec.annotations[actionArgs[0]])
            self.inputSchema = ta.json_schema()
            self.inputType = ta
            self.metadata['inputSchema'] = self.inputSchema
        else:
            self.inputSchema = TypeAdapter(Any).json_schema()
            self.metadata['inputSchema'] = self.inputSchema

        if 'return' in inputSpec.annotations:
            ta = TypeAdapter(inputSpec.annotations['return'])
            self.outputSchema = ta.json_schema()
            self.metadata['outputSchema'] = self.outputSchema
        else:
            self.outputSchema = TypeAdapter(Any).json_schema()
            self.metadata['outputSchema'] = self.outputSchema
