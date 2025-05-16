#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for signal handling functionality."""

import asyncio
import os
import signal
import time
import unittest
from unittest import IsolatedAsyncioTestCase, mock

from genkit.web.manager.signals import SignalHandler


class SignalHandlerTest(unittest.TestCase):
    """Test cases for the SignalHandler class."""

    def setUp(self) -> None:
        """Set up a fresh SignalHandler instance for each test."""
        self.signal_handler = SignalHandler()

    def test_initialization(self) -> None:
        """Test that SignalHandler initializes with expected attributes."""
        handler = SignalHandler()
        self.assertIsInstance(handler.shutdown_event, asyncio.Event)
        self.assertFalse(handler.shutdown_event.is_set())
        self.assertEqual(handler.signal_handlers, {})

    def test_add_handler(self) -> None:
        """Test adding signal handlers."""
        callback1 = mock.Mock()
        callback2 = mock.Mock()

        # Add first handler
        self.signal_handler.add_handler(signal.SIGINT, callback1)
        self.assertIn(signal.SIGINT, self.signal_handler.signal_handlers)
        self.assertIn(callback1, self.signal_handler.signal_handlers[signal.SIGINT])

        # Add second handler for same signal
        self.signal_handler.add_handler(signal.SIGINT, callback2)
        self.assertEqual(len(self.signal_handler.signal_handlers[signal.SIGINT]), 2)
        self.assertIn(callback2, self.signal_handler.signal_handlers[signal.SIGINT])

        # Add handler for different signal
        self.signal_handler.add_handler(signal.SIGTERM, callback1)
        self.assertIn(signal.SIGTERM, self.signal_handler.signal_handlers)
        self.assertIn(callback1, self.signal_handler.signal_handlers[signal.SIGTERM])

    def test_remove_handler(self) -> None:
        """Test removing signal handlers."""
        callback1 = mock.Mock()
        callback2 = mock.Mock()

        # Add handlers
        self.signal_handler.add_handler(signal.SIGINT, callback1)
        self.signal_handler.add_handler(signal.SIGINT, callback2)

        # Remove one handler
        self.signal_handler.remove_handler(signal.SIGINT, callback1)
        self.assertNotIn(callback1, self.signal_handler.signal_handlers[signal.SIGINT])
        self.assertIn(callback2, self.signal_handler.signal_handlers[signal.SIGINT])

        # Remove non-existent handler (should not raise exception)
        self.signal_handler.remove_handler(signal.SIGTERM, callback1)

        # Remove last handler
        self.signal_handler.remove_handler(signal.SIGINT, callback2)
        self.assertIn(signal.SIGINT, self.signal_handler.signal_handlers)
        self.assertEqual(len(self.signal_handler.signal_handlers[signal.SIGINT]), 0)

    def test_handle_signal(self) -> None:
        """Test that handle_signal sets shutdown_event and calls callbacks."""
        callback1 = mock.Mock()
        callback2 = mock.Mock()

        self.signal_handler.add_handler(signal.SIGINT, callback1)
        self.signal_handler.add_handler(signal.SIGINT, callback2)

        # Verify shutdown event is not set
        self.assertFalse(self.signal_handler.shutdown_event.is_set())

        # Handle signal
        self.signal_handler.handle_signal(signal.SIGINT)

        # Verify shutdown event is set
        self.assertTrue(self.signal_handler.shutdown_event.is_set())

        # Verify callbacks were called
        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_handle_signal_with_exception(self) -> None:
        """Test signal handler continues processing even with a callback exception."""
        # First callback will raise an exception
        callback_with_error = mock.Mock(side_effect=Exception('Test error'))
        # Second callback should still be called
        callback_success = mock.Mock()

        self.signal_handler.add_handler(signal.SIGINT, callback_with_error)
        self.signal_handler.add_handler(signal.SIGINT, callback_success)

        # Handle signal
        self.signal_handler.handle_signal(signal.SIGINT)

        # Verify both callbacks were attempted
        callback_with_error.assert_called_once()
        callback_success.assert_called_once()

    def skip_test_real_signal_handling(self) -> None:
        """Test handling of real signals."""
        handler = SignalHandler()

        # Setup a callback that we can check was called
        callback_called = False

        def callback() -> None:
            nonlocal callback_called
            callback_called = True

        handler.add_handler(signal.SIGUSR1, callback)
        handler.setup_signal_handlers()

        # Send the signal to our own process
        os.kill(os.getpid(), signal.SIGUSR1)

        # Give a short time for the signal to be processed
        time.sleep(0.1)

        # Verify the callback was called and shutdown event was set
        self.assertTrue(callback_called)
        self.assertTrue(handler.shutdown_event.is_set())

    def test_setup_signal_handlers(self) -> None:
        """Test that signal handlers are properly registered."""
        with mock.patch('signal.signal') as mock_signal:
            self.signal_handler.setup_signal_handlers()

            # Verify signal.signal was called for expected signals
            # At least SIGINT and SIGTERM
            self.assertGreaterEqual(mock_signal.call_count, 2)

            # Check that SIGINT and SIGTERM were registered
            signals_registered = [call_args[0][0] for call_args in mock_signal.call_args_list]
            self.assertIn(signal.SIGINT, signals_registered)
            self.assertIn(signal.SIGTERM, signals_registered)

            # If on Unix, SIGHUP should also be registered
            if hasattr(signal, 'SIGHUP'):
                self.assertIn(signal.SIGHUP, signals_registered)


class AsyncSignalHandlerTest(IsolatedAsyncioTestCase):
    """Test cases for async functionality of the SignalHandler class."""

    async def test_async_signal_handler(self) -> None:
        """Test the async wrapper for signal handling."""
        signal_handler = SignalHandler()
        # Mock the handle_signal method
        signal_handler.handle_signal = mock.Mock()

        # Call the async signal handler
        await signal_handler.handle_signal_async(signal.SIGINT)

        # Verify handle_signal was called with the signal
        signal_handler.handle_signal.assert_called_once_with(signal.SIGINT)

    async def test_integration(self) -> None:
        """Test the full signal handling flow."""
        handler = SignalHandler()
        callback = mock.Mock()

        # Register callback
        handler.add_handler(signal.SIGINT, callback)

        # Create a task to wait for the shutdown event
        async def wait_for_shutdown() -> bool:
            await handler.shutdown_event.wait()
            return True

        task = asyncio.create_task(wait_for_shutdown())

        # Simulate receiving a signal
        await handler.handle_signal_async(signal.SIGINT)

        # Wait a short time for the task to complete
        done, _ = await asyncio.wait([task], timeout=0.1)

        # Verify the callback was called and the task completed
        callback.assert_called_once()
        self.assertIn(task, done)
        self.assertTrue(await task)
