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

"""Tests for the schema module."""

from pydantic import BaseModel, Field

from genkit.core.schema import to_json_schema


def test_to_json_schema_pydantic_model():
    """Test that a Pydantic model can be converted to a JSON schema."""

    class TestSchema(BaseModel):
        foo: int = Field(None, description='foo field')
        bar: str = Field(None, description='bar field')

    assert to_json_schema(TestSchema) == {
        'properties': {
            'bar': {
                'default': None,
                'description': 'bar field',
                'title': 'Bar',
                'type': 'string',
            },
            'foo': {
                'default': None,
                'description': 'foo field',
                'title': 'Foo',
                'type': 'integer',
            },
        },
        'title': 'TestSchema',
        'type': 'object',
    }


def test_to_json_schema_already_schema():
    """Test that a JSON schema can be converted to a JSON schema."""
    json_schema = {
        'properties': {
            'bar': {
                'default': None,
                'description': 'bar field',
                'title': 'Bar',
                'type': 'string',
            },
            'foo': {
                'default': None,
                'description': 'foo field',
                'title': 'Foo',
                'type': 'integer',
            },
        },
        'title': 'TestSchema',
        'type': 'object',
    }

    assert to_json_schema(json_schema) == json_schema
