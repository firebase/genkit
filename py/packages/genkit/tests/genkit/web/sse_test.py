#!/usr/bin/env python
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the SSE utilities module."""

import json
import unittest

from genkit.web.sse import format_sse, sse_wrapper


class FormatSseTest(unittest.TestCase):
    """Tests for the format_sse function."""

    def test_simple_message(self):
        """Test formatting a simple message."""
        data = {'message': 'Hello, world!'}
        expected = f'data: {json.dumps(data)}\n\n'
        self.assertEqual(format_sse(data), expected)

    def test_nested_dict(self):
        """Test formatting a nested dictionary."""
        data = {
            'user': {
                'name': 'John Doe',
                'age': 30,
                'roles': ['admin', 'user'],
            }
        }
        expected = f'data: {json.dumps(data)}\n\n'
        self.assertEqual(format_sse(data), expected)

    def test_empty_dict(self):
        """Test formatting an empty dictionary."""
        data = {}
        expected = f'data: {json.dumps(data)}\n\n'
        self.assertEqual(format_sse(data), expected)

    def test_special_characters(self):
        """Test formatting a message with special characters."""
        data = {'message': 'Hello, \n"world"!'}
        expected = f'data: {json.dumps(data)}\n\n'
        self.assertEqual(format_sse(data), expected)


async def generate(count=3):
    """Helper to generate test data dictionaries."""
    for i in range(count):
        yield {'message': f'Message {i}'}


async def collect(generator, count=3):
    """Helper to collect events from an async generator."""
    results = []
    async for event in generator:
        results.append(event)
        if len(results) >= count:
            break
    return results


class SseWrapperTest(unittest.IsolatedAsyncioTestCase):
    """Tests for the sse_wrapper function."""

    async def test_basic_wrapping(self):
        """Test basic wrapping of a data generator."""
        results = await collect(sse_wrapper(generate()))
        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            expected_data = {'message': f'Message {i}'}
            self.assertIn(f'id: {i}', result)
            self.assertIn(f'data: {json.dumps(expected_data)}', result)

    async def test_with_event_name(self):
        """Test wrapping with an event name."""
        event_name = 'test_event'
        results = await collect(sse_wrapper(generate(), event=event_name))
        for result in results:
            self.assertIn(f'event: {event_name}', result)

    async def test_with_id_prefix(self):
        """Test wrapping with an ID prefix."""
        id_prefix = 'test'
        results = await collect(sse_wrapper(generate(), id_prefix=id_prefix))
        for i, result in enumerate(results):
            self.assertIn(f'id: {id_prefix}-{i}', result)

    async def test_with_retry(self):
        """Test wrapping with a retry parameter."""
        retry = 3000
        results = await collect(sse_wrapper(generate(), retry=retry))
        for result in results:
            self.assertIn(f'retry: {retry}', result)

    async def test_with_all_parameters(self):
        """Test wrapping with all parameters."""
        event_name = 'test_event'
        id_prefix = 'test'
        retry = 3000
        results = await collect(
            sse_wrapper(
                generate(), event=event_name, id_prefix=id_prefix, retry=retry
            )
        )
        for i, result in enumerate(results):
            expected_data = {'message': f'Message {i}'}
            self.assertIn(f'id: {id_prefix}-{i}', result)
            self.assertIn(f'event: {event_name}', result)
            self.assertIn(f'retry: {retry}', result)
            self.assertIn(f'data: {json.dumps(expected_data)}', result)

    async def test_empty_generator(self):
        """Test wrapping an empty generator."""

        async def empty_generator():
            if False:  # never yields
                yield {}

        results = []
        async for event in sse_wrapper(empty_generator()):
            results.append(event)
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
