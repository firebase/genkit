# Copyright 2022 Google Inc.
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

import inspect
import json
from pydantic import BaseModel, TypeAdapter, Extra, Field
from typing import Union, List, Dict, Optional, Callable, Any, Sequence
from .tracing import tracer


class ActionResponse(BaseModel):
    class Config:
        extra = Extra.forbid

    response: Any
    traceId: str


class Action:
    def __init__(self, type: str, name: str, fn: Callable, description: str | None = None, metadata: Optional[Dict[str, Any]] = None, spanMetadata: Optional[Dict[str, str]] = None):
        self.type = type
        self.name = name

        def fnToCall(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                traceId = str(span.get_span_context().trace_id)
                span.set_attribute('genkit:type', type)
                span.set_attribute('genkit:name', name)

                if spanMetadata != None:
                    for spanMetaKey in spanMetadata:
                        span.set_attribute(
                            spanMetaKey, spanMetadata[spanMetaKey])

                if len(args) > 0:
                    if isinstance(args[0], BaseModel):
                        span.set_attribute(
                            'genkit:input', args[0].model_dump_json())
                    else:
                        span.set_attribute('genkit:input', json.dumps(args[0]))

                output = fn(*args, **kwargs)

                span.set_attribute('genkit:state', 'success')

                if isinstance(output, BaseModel):
                    span.set_attribute(
                        'genkit:output', output.model_dump_json())
                else:
                    span.set_attribute('genkit:output', json.dumps(output))

                return ActionResponse(response=output, traceId=traceId)

        self.fn = fnToCall
        self.description = description
        self.metadata = metadata
        if self.metadata == None:
            self.metadata = {}

        inputSpec = inspect.getfullargspec(fn)
        actionArgs = list(
            filter(lambda k: k != 'return', inputSpec.annotations))
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

        if "return" in inputSpec.annotations:
            ta = TypeAdapter(inputSpec.annotations['return'])
            self.outputSchema = ta.json_schema()
            self.metadata['outputSchema'] = self.outputSchema
        else:
            self.outputSchema = TypeAdapter(Any).json_schema()
            self.metadata['outputSchema'] = self.outputSchema

        pass


class Registry:
    actions: Dict[str, Dict[str, Action]] = {}

    def register_action(self, type: str, name: str, action: Action):
        if type not in self.actions:
            self.actions[type] = {}
        self.actions[type][name] = action

    def lookup_action(self, type: str, name: str):
        if type in self.actions and name in self.actions[type]:
            return self.actions[type][name]
        return None

    def lookup_by_absolute_name(self, name: str):
        tkns = name.split("/", 2)
        return self.lookup_action(tkns[1], tkns[2])
