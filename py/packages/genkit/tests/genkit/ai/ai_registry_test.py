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

from genkit.ai._registry import get_func_description


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


if __name__ == '__main__':
    unittest.main()
