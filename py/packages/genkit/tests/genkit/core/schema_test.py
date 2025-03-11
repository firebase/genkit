# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from genkit.core.schema import to_json_schema
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


def test_to_json_schema_pydantic_model():
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
