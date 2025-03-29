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
    """Record the input metadata for the action.

    Args:
        span: The span to record the metadata for.
        kind: The kind of action.
        name: The name of the action.
        span_metadata: The span metadata to record.
        input: The input to the action.
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
    """Record the output metadata for the action.

    Args:
        span: The span to record the metadata for.
        output: The output to the action.
    """
    span.set_attribute('genkit:state', 'success')
    span.set_attribute('genkit:output', dump_json(output))
