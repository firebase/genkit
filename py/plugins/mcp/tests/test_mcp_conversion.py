# Copyright 2026 Google LLC
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

"""Tests for MCP conversion utilities."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from fakes import mock_mcp_modules

mock_mcp_modules()

from genkit.core.typing import Message
from genkit.plugins.mcp.util import (
    to_mcp_prompt_arguments,
    to_mcp_prompt_message,
    to_mcp_resource_contents,
    to_mcp_tool_result,
)


class TestMessageConversion(unittest.TestCase):
    """Tests for message conversion utilities."""

    def test_convert_user_message(self):
        """Test converting a user message."""
        message = Message(role='user', content=[{'text': 'Hello, world!'}])

        result = to_mcp_prompt_message(message)

        self.assertEqual(result.role, 'user')
        self.assertEqual(result.content.type, 'text')
        self.assertEqual(result.content.text, 'Hello, world!')

    def test_convert_model_message(self):
        """Test converting a model message (maps to assistant)."""
        message = Message(role='model', content=[{'text': 'Hi there!'}])

        result = to_mcp_prompt_message(message)

        self.assertEqual(result.role, 'assistant')
        self.assertEqual(result.content.type, 'text')
        self.assertEqual(result.content.text, 'Hi there!')

    def test_convert_message_with_multiple_text_parts(self):
        """Test converting a message with multiple text parts."""
        message = Message(role='user', content=[{'text': 'Part 1 '}, {'text': 'Part 2 '}, {'text': 'Part 3'}])

        result = to_mcp_prompt_message(message)

        self.assertEqual(result.content.text, 'Part 1 Part 2 Part 3')

    def test_convert_message_with_invalid_role(self):
        """Test that converting a message with invalid role raises error."""
        message = Message(role='system', content=[{'text': 'System message'}])

        with self.assertRaises(ValueError) as context:
            to_mcp_prompt_message(message)

        self.assertIn('system', str(context.exception).lower())

    def test_convert_message_with_image(self):
        """Test converting a message with image content."""
        message = Message(
            role='user', content=[{'media': {'url': 'data:image/png;base64,iVBORw0KG...', 'contentType': 'image/png'}}]
        )

        result = to_mcp_prompt_message(message)

        self.assertEqual(result.role, 'user')
        self.assertEqual(result.content.type, 'image')
        self.assertEqual(result.content.mimeType, 'image/png')

    def test_convert_message_with_non_data_url_fails(self):
        """Test that non-data URLs raise an error."""
        message = Message(role='user', content=[{'media': {'url': 'http://example.com/image.png'}}])

        with self.assertRaises(ValueError) as context:
            to_mcp_prompt_message(message)

        self.assertIn('base64', str(context.exception).lower())


class TestResourceConversion(unittest.TestCase):
    """Tests for resource content conversion."""

    def test_convert_text_resource(self):
        """Test converting text resource content."""
        parts = [{'text': 'Resource content'}]

        result = to_mcp_resource_contents('test://resource', parts)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uri, 'test://resource')
        self.assertEqual(result[0].text, 'Resource content')

    def test_convert_multiple_text_parts(self):
        """Test converting multiple text parts."""
        parts = [{'text': 'Part 1'}, {'text': 'Part 2'}, {'text': 'Part 3'}]

        result = to_mcp_resource_contents('test://resource', parts)

        self.assertEqual(len(result), 3)
        for i, part in enumerate(result, 1):
            self.assertEqual(part.text, f'Part {i}')

    def test_convert_string_parts(self):
        """Test converting string parts."""
        parts = ['Text 1', 'Text 2']

        result = to_mcp_resource_contents('test://resource', parts)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, 'Text 1')
        self.assertEqual(result[1].text, 'Text 2')

    def test_convert_media_resource(self):
        """Test converting media resource content."""
        parts = [{'media': {'url': 'data:image/png;base64,abc123', 'contentType': 'image/png'}}]

        result = to_mcp_resource_contents('test://image', parts)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uri, 'test://image')
        self.assertEqual(result[0].mimeType, 'image/png')
        self.assertEqual(result[0].blob, 'abc123')

    def test_convert_mixed_content(self):
        """Test converting mixed text and media content."""
        parts = [{'text': 'Description'}, {'media': {'url': 'data:image/png;base64,xyz', 'contentType': 'image/png'}}]

        result = to_mcp_resource_contents('test://mixed', parts)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, 'Description')
        self.assertEqual(result[1].blob, 'xyz')


class TestToolResultConversion(unittest.TestCase):
    """Tests for tool result conversion."""

    def test_convert_string_result(self):
        """Test converting string result."""
        result = to_mcp_tool_result('Hello, world!')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, 'text')
        self.assertEqual(result[0].text, 'Hello, world!')

    def test_convert_dict_result(self):
        """Test converting dict result."""
        result = to_mcp_tool_result({'key': 'value', 'number': 42})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, 'text')
        # Should be JSON serialized
        import json

        parsed = json.loads(result[0].text)
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['number'], 42)

    def test_convert_number_result(self):
        """Test converting number result."""
        result = to_mcp_tool_result(42)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, '42')

    def test_convert_boolean_result(self):
        """Test converting boolean result."""
        result = to_mcp_tool_result(True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, 'True')


class TestSchemaConversion(unittest.TestCase):
    """Tests for schema conversion utilities."""

    def test_convert_simple_schema(self):
        """Test converting simple string schema."""
        schema = {'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'User name'}}}

        result = to_mcp_prompt_arguments(schema)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'name')
        self.assertEqual(result[0]['description'], 'User name')

    def test_convert_schema_with_required(self):
        """Test converting schema with required fields."""
        schema = {
            'type': 'object',
            'properties': {'name': {'type': 'string'}, 'age': {'type': 'string'}},
            'required': ['name'],
        }

        result = to_mcp_prompt_arguments(schema)

        name_arg = next(arg for arg in result if arg['name'] == 'name')
        age_arg = next(arg for arg in result if arg['name'] == 'age')

        self.assertTrue(name_arg['required'])
        self.assertFalse(age_arg['required'])

    def test_convert_schema_with_non_string_fails(self):
        """Test that non-string properties raise an error."""
        schema = {'type': 'object', 'properties': {'count': {'type': 'number'}}}

        with self.assertRaises(ValueError) as context:
            to_mcp_prompt_arguments(schema)

        self.assertIn('string', str(context.exception).lower())

    def test_convert_schema_with_union_type(self):
        """Test converting schema with union type including string."""
        schema = {'type': 'object', 'properties': {'value': {'type': ['string', 'null']}}}

        result = to_mcp_prompt_arguments(schema)

        # Should succeed because string is in the union
        self.assertEqual(len(result), 1)

    def test_convert_none_schema(self):
        """Test converting None schema."""
        result = to_mcp_prompt_arguments(None)

        self.assertIsNone(result)

    def test_convert_schema_without_properties_fails(self):
        """Test that schema without properties raises an error."""
        schema = {'type': 'object'}

        with self.assertRaises(ValueError) as context:
            to_mcp_prompt_arguments(schema)

        self.assertIn('properties', str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()
