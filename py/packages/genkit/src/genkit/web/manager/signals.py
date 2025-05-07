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

"""Signal handling functionality for asyncio applications.

This module provides a robust SignalHandler class that manages system signals
(like SIGINT, SIGTERM, SIGHUP) in asyncio applications with the following
features:

1. Thread-safe signal handling: Properly bridges traditional signal handlers
    with the asyncio event loop.

2. Callback registration system: Allows registering and unregistering multiple
   callbacks for specific signals, enabling modular signal response.

3. Centralized shutdown coordination: Uses an asyncio.Event that can be awaited
   by server components for clean, coordinated shutdown.

4. Exception safety: Isolates callback failures to prevent cascade failures
   during shutdown.

Typical usage:

    ```python
    # Create a signal handler instance
    signal_handler = SignalHandler()

    # Setup signal handling (ideally in the main thread)
    signal_handler.setup_signal_handlers()

    # Register a callback for a specific signal
    signal_handler.add_handler(signal.SIGTERM, my_cleanup_function)


    # Use the shutdown event to coordinate graceful shutdown
    async def server_main():
        # Start your services...

        # Wait for shutdown signal
        await signal_handler.shutdown_event.wait()

        # Perform cleanup
        await cleanup()
    ```

When a signal is received:

1. The SignalHandler sets the shutdown_event.
2. All registered callbacks for that signal are executed.
3. Components awaiting the shutdown_event can perform cleanup.

This approach allows for graceful shutdown of asyncio applications, ensuring
resources are properly released and pending operations can be completed.
"""

import asyncio
import os
import signal
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def kill_all_servers() -> None:
    """Kills all servers registered with the signal handler."""
    loop = asyncio.get_running_loop()
    loop.call_soon(os.kill, os.getpid(), signal.SIGKILL)


def terminate_all_servers() -> None:
    """Terminate all servers registered with the signal handler."""
    loop = asyncio.get_running_loop()
    loop.call_soon(os.kill, os.getpid(), signal.SIGTERM)


class SignalHandler:
    """Handles system signals and manages callbacks for asyncio applications.

    This class provides a comprehensive solution for handling system signals in
    asyncio applications. It creates a bridge between the traditional signal
    handlers (which run in the main thread) and the asyncio event loop, ensuring
    signals are properly handled regardless of which thread receives them.

    ### Key components

    1. shutdown_event (asyncio.Event): A central coordination point that gets
       set when shutdown signals are received. Server components can await this
       event to know when to initiate graceful shutdown.

    2. signal_handlers (dict): A registry of callbacks mapped to specific
       signals, allowing different components to register for notification when
       particular signals occur.

    3. Thread safety: The handler uses asyncio.create_task to safely schedule
       signal handling in the event loop regardless of which thread receives the
       signal.

    4. Exception isolation: Each callback is executed in isolation, preventing
       one failing callback from blocking others during the critical shutdown
       phase.

    The class handles common signals like SIGINT (Ctrl+C), SIGTERM (termination
    request), and SIGHUP (terminal disconnect) on systems that support it. It
    properly coordinates these signals with the asyncio event loop to ensure
    clean shutdown.

    ### Key operations

    | Operation                 | Description                                             |
    |---------------------------|---------------------------------------------------------|
    | `add_handler()`           | Register a callback function for a specific signal      |
    | `remove_handler()`        | Remove a previously registered callback for a signal    |
    | `setup_signal_handlers()` | Configure handlers for common signals (SIGINT, SIGTERM) |
    | `handle_signal()`         | Process signals and execute registered callbacks        |
    | `handle_signal_async()`   | Async wrapper for signal handling in asyncio            |
    """

    def __init__(self) -> None:
        """Initialize the signal handler."""
        self.shutdown_event = asyncio.Event()
        self.signal_handlers: dict[int, set[Callable[[], Any]]] = {}

    def add_handler(self, sig: int, callback: Callable[[], Any]) -> None:
        """Add a callback for a specific signal.

        Args:
            sig: Signal number (e.g., signal.SIGINT, signal.SIGTERM)
            callback: Function to call when the signal is received

        Returns:
            None
        """
        if sig not in self.signal_handlers:
            self.signal_handlers[sig] = set()

        self.signal_handlers[sig].add(callback)

    def remove_handler(self, sig: int, callback: Callable[[], Any]) -> None:
        """Remove a callback for a specific signal.

        Args:
            sig: Signal number (e.g., signal.SIGINT, signal.SIGTERM)
            callback: Function to remove

        Returns:
            None
        """
        if sig in self.signal_handlers and callback in self.signal_handlers[sig]:
            self.signal_handlers[sig].remove(callback)

    def setup_signal_handlers(self) -> None:
        """Setup handlers for common signals.

        Returns:
            None
        """

        # Define signal handler function that works in the main thread
        def _handle_signal(sig: int, frame: Any) -> None:
            """Handle received signal.

            Args:
                sig: Signal number (e.g., signal.SIGINT, signal.SIGTERM)
                frame: Current stack frame

            Returns:
                None
            """
            # Use the event loop to schedule our signal handler
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.handle_signal_async(sig))
            else:
                # Direct call if event loop is not running (unlikely)
                self.handle_signal(sig)

        # Register for common shutdown signals
        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
            # On Unix systems, we can also handle SIGHUP
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, _handle_signal)
        except ValueError as e:
            # This can happen if we're not in the main thread
            logger.warning('Could not set up signal handlers', error=e)

    def handle_signal(self, sig: int) -> None:
        """Process a received signal.

        Args:
            sig: Signal number (e.g., signal.SIGINT, signal.SIGTERM)

        Returns:
            None
        """
        logger.info('Received signal', signal=sig)

        # Set shutdown event
        self.shutdown_event.set()

        # Call registered handlers
        if sig in self.signal_handlers:
            for callback in self.signal_handlers[sig]:
                try:
                    callback()
                except Exception as e:
                    logger.error('Error in signal handler callback', error=e)

    async def handle_signal_async(self, sig: int) -> None:
        """Async wrapper for the signal handler.

        Args:
            sig: Signal number (e.g., signal.SIGINT, signal.SIGTERM)

        Returns:
            None
        """
        self.handle_signal(sig)
