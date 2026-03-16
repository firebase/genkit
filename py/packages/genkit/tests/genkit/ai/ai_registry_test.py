#!/usr/bin/env python3
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

"""Tests for the AI registry module.

This module contains unit tests for the GenkitRegistry class and its associated
functionality, ensuring proper registration and management of Genkit resources.

Test Coverage
=============

┌─────────────────────────────────────────────────────────────────────────────┐
│ Test Case                           │ Description                           │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ get_func_description Tests                                                  │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ test_with_explicit_description      │ Explicit desc takes precedence        │
│ test_with_docstring                 │ Docstring used when no explicit desc  │
│ test_without_docstring              │ Empty string when no docstring        │
│ test_with_none_docstring            │ Empty string when docstring is None   │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ define_json_schema Tests                                                    │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ test_define_json_schema_basic       │ Register a basic JSON schema          │
│ test_define_json_schema_complex     │ Register complex nested schema        │
│ test_define_json_schema_returns     │ Method returns the schema             │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ define_dynamic_action_provider Tests                                        │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ test_define_dap_with_string         │ DAP with string config                │
│ test_define_dap_with_config         │ DAP with DapConfig object             │
│ test_define_dap_returns_provider    │ Method returns DynamicActionProvider  │
└─────────────────────────────────────┴───────────────────────────────────────┘
"""

import unittest

import pytest

from genkit.ai import Genkit
from genkit.ai._registry import get_func_description
from genkit.blocks.dap import DapCacheConfig, DapConfig, DapValue, DynamicActionProvider


class TestGetFuncDescription(unittest.TestCase):
    """Test the get_func_description function."""

    def test_get_func_description_with_explicit_description(self) -> None:
        """Test that explicit description takes precedence over docstring."""

        def test_func() -> None:
            """This docstring should be ignored."""
            pass

        description = get_func_description(test_func, 'Explicit description')
        self.assertEqual(description, 'Explicit description')

    def test_get_func_description_with_docstring(self) -> None:
        """Test that docstring is used when no explicit description is provided."""

        def test_func() -> None:
            """This is the function's docstring."""
            pass

        description = get_func_description(test_func)
        self.assertEqual(description, "This is the function's docstring.")

    def test_get_func_description_without_docstring(self) -> None:
        """Test that empty string is returned when no docstring is present."""

        def test_func() -> None:
            pass

        description = get_func_description(test_func)
        self.assertEqual(description, '')

    def test_get_func_description_with_none_docstring(self) -> None:
        """Test that empty string is returned when docstring is None."""

        def test_func() -> None:
            pass

        test_func.__doc__ = None

        description = get_func_description(test_func)
        self.assertEqual(description, '')


class TestDefineJsonSchema:
    """Tests for the define_json_schema method."""

    def test_define_json_schema_basic(self) -> None:
        """Test registering a basic JSON schema."""
        ai = Genkit()

        schema = ai.define_json_schema(
            'SimpleObject',
            {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'age': {'type': 'integer'},
                },
                'required': ['name'],
            },
        )

        assert schema is not None
        assert schema['type'] == 'object'
        assert 'properties' in schema

    def test_define_json_schema_complex(self) -> None:
        """Test registering a complex nested JSON schema."""
        ai = Genkit()

        schema = ai.define_json_schema(
            'Recipe',
            {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'ingredients': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                    'instructions': {'type': 'string'},
                    'nutrition': {
                        'type': 'object',
                        'properties': {
                            'calories': {'type': 'number'},
                            'protein': {'type': 'number'},
                        },
                    },
                },
                'required': ['title', 'ingredients', 'instructions'],
            },
        )

        assert schema is not None
        assert schema['type'] == 'object'
        # Type checker doesn't narrow dict[str, object] properly after isinstance
        properties: dict[str, object] = schema['properties']  # type: ignore[assignment]
        assert isinstance(properties, dict)
        assert 'ingredients' in properties
        ingredients: dict[str, object] = properties['ingredients']  # type: ignore[assignment]
        assert isinstance(ingredients, dict)
        assert ingredients['type'] == 'array'

    def test_define_json_schema_returns_same_schema(self) -> None:
        """Test that define_json_schema returns the schema for convenience."""
        ai = Genkit()

        input_schema: dict[str, object] = {
            'type': 'string',
            'minLength': 1,
        }

        returned_schema = ai.define_json_schema('StringSchema', input_schema)

        # Should return the same schema object
        assert returned_schema is input_schema


class TestDefineDynamicActionProvider:
    """Tests for the define_dynamic_action_provider method via Genkit."""

    @pytest.mark.asyncio
    async def test_define_dap_with_string_config(self) -> None:
        """Test defining a DAP with a string name."""
        ai = Genkit()

        async def dap_fn() -> DapValue:
            return {}

        dap = ai.define_dynamic_action_provider('my-dap', dap_fn)

        assert isinstance(dap, DynamicActionProvider)
        assert dap.config.name == 'my-dap'

    @pytest.mark.asyncio
    async def test_define_dap_with_config_object(self) -> None:
        """Test defining a DAP with a DapConfig object."""
        ai = Genkit()

        async def dap_fn() -> DapValue:
            return {}

        config = DapConfig(
            name='configured-dap',
            description='A configured DAP',
            cache_config=DapCacheConfig(ttl_millis=5000),
            metadata={'custom': 'value'},
        )

        dap = ai.define_dynamic_action_provider(config, dap_fn)

        assert isinstance(dap, DynamicActionProvider)
        assert dap.config.name == 'configured-dap'
        assert dap.config.description == 'A configured DAP'
        assert dap.config.cache_config is not None
        assert dap.config.cache_config.ttl_millis == 5000

    @pytest.mark.asyncio
    async def test_define_dap_returns_provider(self) -> None:
        """Test that define_dynamic_action_provider returns a DynamicActionProvider."""
        ai = Genkit()

        async def dap_fn() -> DapValue:
            return {}

        result = ai.define_dynamic_action_provider('test-dap', dap_fn)

        assert isinstance(result, DynamicActionProvider)
        # Should have required methods
        assert hasattr(result, 'get_action')
        assert hasattr(result, 'list_action_metadata')
        assert hasattr(result, 'invalidate_cache')
        assert hasattr(result, 'get_action_metadata_record')


if __name__ == '__main__':
    unittest.main()
