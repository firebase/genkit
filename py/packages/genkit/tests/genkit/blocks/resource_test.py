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

"""Unit tests for resource registration and URI matching."""

import unittest

import pytest

from genkit.ai import Genkit
from genkit.blocks.resource import ResourceContent, ResourceOptions, matches_uri_template
from genkit.core.action.types import ActionKind


class TestResourceRegistration(unittest.TestCase):
    """Tests for resource registration in Genkit registry."""

    def setUp(self):
        """Set up test fixtures."""
        self.ai = Genkit()

    def test_define_resource_with_fixed_uri(self):
        """Test defining a resource with a fixed URI."""

        def my_resource(req):
            return {'content': [{'text': 'test content'}]}

        action = self.ai.define_resource(name='test_resource', uri='test://resource', fn=my_resource)

        # Verify action was registered
        self.assertIsNotNone(action)
        self.assertEqual(action.name, 'test_resource')
        self.assertEqual(action.kind, ActionKind.RESOURCE)

        # Verify metadata
        self.assertIn('resource', action.metadata)
        self.assertEqual(action.metadata['resource']['uri'], 'test://resource')

    def test_define_resource_with_template(self):
        """Test defining a resource with a URI template."""

        def file_resource(req):
            return {'content': [{'text': f'contents of {req["uri"]}'}]}

        action = self.ai.define_resource(name='file', template='file://{path}', fn=file_resource)

        # Verify action was registered
        self.assertIsNotNone(action)
        self.assertEqual(action.name, 'file')

        # Verify metadata
        self.assertIn('resource', action.metadata)
        self.assertEqual(action.metadata['resource']['template'], 'file://{path}')

    def test_define_resource_requires_uri_or_template(self):
        """Test that defining a resource requires either uri or template."""

        def my_resource(req):
            return {'content': [{'text': 'test'}]}

        with self.assertRaises(ValueError) as context:
            self.ai.define_resource(name='invalid_resource', fn=my_resource)

        self.assertIn('uri', str(context.exception).lower())
        self.assertIn('template', str(context.exception).lower())

    def test_define_resource_with_description(self):
        """Test defining a resource with a description."""

        def my_resource(req):
            return {'content': [{'text': 'test'}]}

        action = self.ai.define_resource(
            name='described_resource', uri='test://resource', description='Test resource description', fn=my_resource
        )

        self.assertEqual(action.description, 'Test resource description')

    def test_define_resource_with_metadata(self):
        """Test defining a resource with custom metadata."""

        def my_resource(req):
            return {'content': [{'text': 'test'}]}

        custom_metadata = {'custom_key': 'custom_value', 'mcp': {'_meta': {'version': '1.0'}}}

        action = self.ai.define_resource(
            name='meta_resource', uri='test://resource', metadata=custom_metadata, fn=my_resource
        )

        self.assertIn('custom_key', action.metadata)
        self.assertEqual(action.metadata['custom_key'], 'custom_value')
        self.assertIn('mcp', action.metadata)


class TestURITemplateMatching(unittest.TestCase):
    """Tests for URI template matching functionality."""

    def test_exact_match(self):
        """Test exact URI matching without parameters."""
        template = 'file:///exact/path'
        uri = 'file:///exact/path'

        result = matches_uri_template(template, uri)
        self.assertIsNotNone(result)
        self.assertEqual(result, {})

    def test_single_parameter_match(self):
        """Test URI template with single parameter."""
        template = 'file://{path}'
        uri = 'file:///home/user/document.txt'

        result = matches_uri_template(template, uri)
        self.assertIsNotNone(result)
        self.assertIn('path', result)
        self.assertEqual(result['path'], '/home/user/document.txt')

    def test_multiple_parameters_match(self):
        """Test URI template with multiple parameters."""
        template = 'user://{user_id}/profile/{section}'
        uri = 'user://12345/profile/settings'

        result = matches_uri_template(template, uri)
        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], '12345')
        self.assertEqual(result['section'], 'settings')

    def test_no_match(self):
        """Test URI that doesn't match template."""
        template = 'file://{path}'
        uri = 'http://example.com/file.txt'

        result = matches_uri_template(template, uri)
        self.assertIsNone(result)

    def test_partial_match_fails(self):
        """Test that partial matches fail."""
        template = 'file://{path}/document.txt'
        uri = 'file:///home/user/other.txt'

        result = matches_uri_template(template, uri)
        self.assertIsNone(result)

    def test_complex_template(self):
        """Test complex URI template with multiple segments."""
        template = 'api://{version}/users/{user_id}/posts/{post_id}'
        uri = 'api://v2/users/alice/posts/42'

        result = matches_uri_template(template, uri)
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], 'v2')
        self.assertEqual(result['user_id'], 'alice')
        self.assertEqual(result['post_id'], '42')

    def test_special_characters_in_uri(self):
        """Test URI with special characters."""
        template = 'file://{path}'
        uri = 'file:///path/with-dashes_and_underscores.txt'

        result = matches_uri_template(template, uri)
        self.assertIsNotNone(result)
        # Note: The current implementation uses [^/]+ which may not capture all special chars
        # This test documents current behavior

    def test_empty_parameter(self):
        """Test template matching with empty parameter."""
        template = 'resource://{id}/data'
        uri = 'resource:///data'

        result = matches_uri_template(template, uri)
        # Should not match because {id} expects at least one character
        self.assertIsNone(result)


@pytest.mark.asyncio
class TestResourceExecution(unittest.IsolatedAsyncioTestCase):
    """Tests for executing resource actions."""

    async def test_execute_fixed_uri_resource(self):
        """Test executing a resource with fixed URI."""
        ai = Genkit()

        def my_resource(req):
            return {'content': [{'text': 'Hello from resource!'}]}

        action = ai.define_resource(name='greeting', uri='app://greeting', fn=my_resource)

        # Execute the resource
        result = await action.arun({'uri': 'app://greeting'})

        self.assertIn('content', result.response)
        self.assertEqual(len(result.response['content']), 1)
        self.assertEqual(result.response['content'][0]['text'], 'Hello from resource!')

    async def test_execute_template_resource(self):
        """Test executing a resource with URI template."""
        ai = Genkit()

        def user_profile(req):
            user_id = req.get('user_id')
            return {'content': [{'text': f'Profile for user {user_id}'}]}

        action = ai.define_resource(name='user_profile', template='user://{user_id}/profile', fn=user_profile)

        # Execute the resource
        result = await action.arun({'uri': 'user://alice/profile'})

        self.assertIn('content', result.response)
        self.assertEqual(result.response['content'][0]['text'], 'Profile for user alice')

    async def test_resource_with_multiple_content_parts(self):
        """Test resource returning multiple content parts."""
        ai = Genkit()

        def multi_part_resource(req):
            return {'content': [{'text': 'Part 1'}, {'text': 'Part 2'}, {'text': 'Part 3'}]}

        action = ai.define_resource(name='multi', uri='test://multi', fn=multi_part_resource)

        result = await action.arun({'uri': 'test://multi'})

        self.assertEqual(len(result.response['content']), 3)
        self.assertEqual(result.response['content'][0]['text'], 'Part 1')
        self.assertEqual(result.response['content'][1]['text'], 'Part 2')
        self.assertEqual(result.response['content'][2]['text'], 'Part 3')

    async def test_async_resource_function(self):
        """Test resource with async function."""
        ai = Genkit()

        async def async_resource(req):
            # Simulate async operation
            import asyncio

            await asyncio.sleep(0.01)
            return {'content': [{'text': 'Async result'}]}

        action = ai.define_resource(name='async_res', uri='test://async', fn=async_resource)

        result = await action.arun({'uri': 'test://async'})

        self.assertEqual(result.response['content'][0]['text'], 'Async result')


if __name__ == '__main__':
    unittest.main()
