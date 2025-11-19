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
"""

import unittest

from genkit.ai._registry import GenkitRegistry, get_func_description
from genkit.core.typing import EmbedRequest, EmbedResponse,Embedding


class TestGetFuncDescription(unittest.TestCase):
    """Test the get_func_description function."""

    def test_get_func_description_with_explicit_description(self) -> None:
        """Test that explicit description takes precedence over docstring."""

        def test_func():
            """This docstring should be ignored."""
            pass

        description = get_func_description(test_func, 'Explicit description')
        self.assertEqual(description, 'Explicit description')

    def test_get_func_description_with_docstring(self) -> None:
        """Test that docstring is used when no explicit description is provided."""

        def test_func():
            """This is the function's docstring."""
            pass

        description = get_func_description(test_func)
        self.assertEqual(description, "This is the function's docstring.")

    def test_get_func_description_without_docstring(self) -> None:
        """Test that empty string is returned when no docstring is present."""

        def test_func():
            pass

        description = get_func_description(test_func)
        self.assertEqual(description, '')

    def test_get_func_description_with_none_docstring(self) -> None:
        """Test that empty string is returned when docstring is None."""

        def test_func():
            pass

        test_func.__doc__ = None

        description = get_func_description(test_func)
        self.assertEqual(description, '')
class TestRegistryEmbedder(unittest.TestCase):
    """Test embedder registration in GenkitRegistry."""

    def test_define_embedder_registration(self) -> None:
        """Test that define_embedder registers embedder in registry."""

        def mock_embedder_fn(request: EmbedRequest) -> EmbedResponse:
            return EmbedResponse(embeddings=[Embedding(embedding=[0.1, 0.2])])

        registry = GenkitRegistry()

        action = registry.define_embedder(
            name='test-embedder',
            fn=mock_embedder_fn,
            config_schema=None,
            metadata=None,
            description='Test embedder'
        )

        self.assertEqual(action.name, 'test-embedder')
        self.assertEqual(action.kind.value, 'embedder')

        from genkit.core.action.types import ActionKind
        registered_action = registry.registry.lookup_action(ActionKind.EMBEDDER, 'test-embedder')
        self.assertIsNotNone(registered_action)
        self.assertEqual(registered_action.name, 'test-embedder')

    def test_define_embedder_with_metadata_and_info(self) -> None:
        """Test that define_embedder properly extracts info from metadata."""

        def mock_embedder_fn(request: EmbedRequest) -> EmbedResponse:
            return EmbedResponse(embeddings=[Embedding(embedding=[0.1, 0.2])])

        registry = GenkitRegistry()

        metadata = {
            'embedder': {
                'dimensions': 768,
                'label': 'Test Embedder',
                'customOptions': {'should': 'be excluded'}
            }
        }

        action = registry.define_embedder(
            name='test-embedder-with-info',
            fn=mock_embedder_fn,
            config_schema=None,
            metadata=metadata,
            description='Test embedder with info'
        )

        self.assertEqual(action.name, 'test-embedder-with-info')
        self.assertEqual(action.kind.value, 'embedder')
        self.assertEqual(action.description, 'Test embedder with info')

        self.assertIn('embedder', action.metadata)
        embedder_meta = action.metadata['embedder']

if __name__ == '__main__':
    unittest.main()
