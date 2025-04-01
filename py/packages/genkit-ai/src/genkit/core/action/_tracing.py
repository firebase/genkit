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

"""Action tracing module for defining and managing action tracing."""

from genkit.codec import dump_json


def record_input_metadata(span, kind, name, span_metadata, input):
    """Records input metadata onto an OpenTelemetry span for a Genkit action.

    Sets standard Genkit attributes like action type, subtype (kind), name,
    and the JSON representation of the input. Also adds any custom span
    metadata provided.

    Args:
        span: The OpenTelemetry Span object to add attributes to.
        kind: The kind (e.g., 'model', 'flow') of the action.
        name: The specific name of the action.
        span_metadata: An optional dictionary of custom key-value pairs to add
                       as span attributes.
        input: The input data provided to the action.
    """
    span.set_attribute('genkit:type', 'action')
    span.set_attribute('genkit:metadata:subtype', kind)
    span.set_attribute('genkit:name', name)
    if input is not None:
        span.set_attribute('genkit:input', dump_json(input))

    if span_metadata is not None:
        for meta_key in span_metadata:
            span.set_attribute(meta_key, span_metadata[meta_key])


def record_output_metadata(span, output) -> None:
    """Records output metadata onto an OpenTelemetry span for a Genkit action.

    Marks the span state as 'success' and records the JSON representation of
    the action's output.

    Args:
        span: The OpenTelemetry Span object to add attributes to.
        output: The output data returned by the action.
    """
    span.set_attribute('genkit:state', 'success')
    span.set_attribute('genkit:output', dump_json(output))
