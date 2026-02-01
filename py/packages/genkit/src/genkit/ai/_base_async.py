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

"""Asynchronous server gateway interface implementation for Genkit."""

import signal
import urllib.request
from collections.abc import Coroutine
from typing import Any, TypeVar

import anyio
import uvicorn

from genkit.aio.loop import run_loop
from genkit.blocks.formats import built_in_formats
from genkit.blocks.generate import define_generate_action
from genkit.core.environment import is_dev_environment
from genkit.core.logging import get_logger
from genkit.core.plugin import Plugin
from genkit.core.reflection import (
    ReflectionClientV2,
    get_reflection_v2_url,
)
from genkit.core.reflection_v1 import create_reflection_asgi_app
from genkit.core.registry import Registry
from genkit.web.manager._ports import find_free_port_sync

from ._registry import GenkitRegistry
from ._runtime import RuntimeManager
from ._server import ServerSpec

logger = get_logger(__name__)

T = TypeVar('T')


class GenkitBase(GenkitRegistry):
    """Base class with shared infra for Genkit instances (sync and async)."""

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
        reflection_server_spec: ServerSpec | None = None,
    ) -> None:
        """Initialize a new Genkit instance.

        Args:
            plugins: List of plugins to initialize.
            model: Model name to use.
            reflection_server_spec: Server spec for the reflection
                server. If not provided in dev mode, a default will be used.
        """
        super().__init__()
        self._reflection_server_spec: ServerSpec | None = reflection_server_spec
        self._initialize_registry(model, plugins)
        # Ensure the default generate action is registered for async usage.
        define_generate_action(self.registry)

    def _initialize_registry(self, model: str | None, plugins: list[Plugin] | None) -> None:
        """Initialize the registry for the Genkit instance.

        Args:
            model: Model name to use.
            plugins: List of plugins to initialize.

        Raises:
            ValueError: If an invalid plugin is provided.

        Returns:
            None
        """
        self.registry.default_model = model
        for fmt in built_in_formats:
            self.define_format(fmt)

        if not plugins:
            logger.warning('No plugins provided to Genkit')
        else:
            for plugin in plugins:
                if isinstance(plugin, Plugin):  # pyright: ignore[reportUnnecessaryIsInstance]
                    self.registry.register_plugin(plugin)
                else:
                    raise ValueError(f'Invalid {plugin=} provided to Genkit: must be of type `genkit.ai.Plugin`')

    def run_main(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run the user's main coroutine.

        In development mode (`GENKIT_ENV=dev`), this starts the Genkit
        reflection server and runs the user's coroutine concurrently within the
        same event loop, blocking until the server is stopped (e.g., via
        Ctrl+C).

        In production mode, this simply runs the user's coroutine to completion
        using `uvloop.run()` for performance if available, otherwise
        `asyncio.run()`.

        Args:
            coro: The main coroutine provided by the user.

        Returns:
            The result of the user's coroutine.
        """
        if not is_dev_environment():
            logger.info('Running in production mode.')
            return run_loop(coro)

        logger.info('Running in development mode.')

        spec = self._reflection_server_spec
        if not spec:
            spec = ServerSpec(scheme='http', host='127.0.0.1', port=find_free_port_sync(3100, 3999))
        assert spec is not None  # Type narrowing: spec is guaranteed non-None after the above check

        async def dev_runner() -> T:
            """Internal async function to run tasks using AnyIO TaskGroup."""
            # Assert for type narrowing inside closure (pyrefly doesn't propagate from outer scope)
            assert spec is not None
            # Capture spec in local var for nested functions (pyrefly doesn't narrow closures)
            server_spec: ServerSpec = spec
            user_result: T | None = None
            user_task_finished_event = anyio.Event()

            async def run_user_coro_wrapper() -> None:
                """Wraps user coroutine to capture result and signal completion."""
                nonlocal user_result
                try:
                    user_result = await coro
                    logger.debug('User coroutine completed successfully.')
                except Exception as err:
                    # Log error but don't necessarily stop the server
                    logger.error(f'User coroutine failed: {err}', exc_info=True)
                    # Store exception? Or let TaskGroup handle it if critical?
                    # Depending on desired behavior, could raise here to stop everything.
                    pass  # Continue running server for now
                finally:
                    user_task_finished_event.set()

            # Setup signal handlers for graceful shutdown (parity with JS)

            # Actually, anyio.run handles Ctrl+C (SIGINT) by raising KeyboardInterrupt/CancelledError
            # For SIGTERM, we might need to be explicit if we run in a container/process manager.
            # JS uses: process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);

            # Since anyio/asyncio handles SIGINT well, let's add a task to catch SIGTERM
            async def handle_sigterm(tg_to_cancel: anyio.abc.TaskGroup) -> None:  # type: ignore[name-defined]
                with anyio.open_signal_receiver(signal.SIGTERM) as signals:
                    async for _signum in signals:
                        logger.info('Received SIGTERM, cancelling tasks...')
                        tg_to_cancel.cancel_scope.cancel()
                        return

            try:
                # Check if Reflection API v2 is enabled
                v2_url = get_reflection_v2_url()

                if v2_url:
                    # Reflection API v2: Use WebSocket client connecting to runtime manager
                    client = ReflectionClientV2(self.registry, v2_url)

                    async with anyio.create_task_group() as tg:
                        # Start v2 client in background (handles its own reconnection)
                        tg.start_soon(client.run, name='genkit-reflection-v2-client')
                        await logger.ainfo(f'Started Genkit Reflection v2 client connecting to {v2_url}')

                        # Start SIGTERM handler
                        tg.start_soon(handle_sigterm, tg, name='genkit-sigterm-handler')

                        # Start the user coroutine
                        tg.start_soon(run_user_coro_wrapper, name='genkit-user-coroutine')
                        await logger.ainfo('Started Genkit user coroutine')

                        # Block here until the task group is canceled (e.g. Ctrl+C)
                        # or a task raises an unhandled exception

                else:
                    # Reflection API v1: Start HTTP server
                    await _run_v1_reflection_server(
                        registry=self.registry,
                        server_spec=server_spec,
                        handle_sigterm=handle_sigterm,
                        run_user_coro_wrapper=run_user_coro_wrapper,
                    )

            except anyio.get_cancelled_exc_class():
                logger.info('Development server task group cancelled (e.g., Ctrl+C).')
                raise
            except Exception:
                logger.exception('Development server task group error')
                raise

            # After the TaskGroup finishes (error or cancelation).
            if user_task_finished_event.is_set():
                await logger.adebug('User coroutine finished before TaskGroup exit.')
                if user_result is None:
                    raise RuntimeError('User coroutine finished without a result.')
                return user_result

            await logger.adebug('User coroutine did not finish before TaskGroup exit.')
            raise RuntimeError('User coroutine did not finish before TaskGroup exit.')

        return anyio.run(dev_runner)


async def _run_v1_reflection_server(
    registry: Registry,
    server_spec: ServerSpec,
    handle_sigterm: Any,  # noqa: ANN401 - callback type is complex
    run_user_coro_wrapper: Any,  # noqa: ANN401 - callback type is complex
) -> None:
    """Run the Reflection API v1 HTTP server with health checking.

    This function encapsulates all V1 server startup logic including:
    - Creating and starting the uvicorn server
    - Managing the runtime file lifecycle
    - Polling for server health before writing the runtime file
    - Starting the user coroutine and SIGTERM handler

    Args:
        registry: The Genkit registry.
        server_spec: Server specification (host, port, scheme).
        handle_sigterm: Callback to handle SIGTERM signals.
        run_user_coro_wrapper: The user's coroutine wrapped for execution.
    """
    reflection_server = _make_reflection_server(registry, server_spec)

    # Use lazy_write=True to prevent race condition where file exists before server is up
    async with RuntimeManager(server_spec, lazy_write=True) as runtime_manager:
        async with anyio.create_task_group() as tg:
            # Start reflection server in the background.
            tg.start_soon(reflection_server.serve, name='genkit-reflection-server')
            await logger.ainfo(f'Started Genkit reflection server at {server_spec.url}')

            # Start SIGTERM handler
            tg.start_soon(handle_sigterm, tg, name='genkit-sigterm-handler')

            # Poll for server readiness before writing runtime file
            await _wait_for_server_health(server_spec)

            # Now write the runtime file
            _ = runtime_manager.write_runtime_file()

            # Start the user coroutine
            tg.start_soon(run_user_coro_wrapper, name='genkit-user-coroutine')
            await logger.ainfo('Started Genkit user coroutine')

            # Block here until the task group is canceled (e.g. Ctrl+C)
            # or a task raises an unhandled exception


async def _wait_for_server_health(server_spec: ServerSpec, max_retries: int = 20) -> None:
    """Wait for the reflection server to become healthy.

    Polls the health endpoint until it responds successfully or max retries reached.

    Args:
        server_spec: Server specification with URL.
        max_retries: Maximum number of retry attempts (default 20, ~2 seconds total).
    """
    for _i in range(max_retries):
        try:

            def check_health() -> bool:
                health_url = f'{server_spec.url}/api/__health'
                with urllib.request.urlopen(health_url, timeout=0.5) as response:
                    return response.status == 200

            is_healthy = await anyio.to_thread.run_sync(check_health)  # type: ignore[attr-defined]
            if is_healthy:
                return
        except Exception:
            await anyio.sleep(0.1)

    logger.warning(f'Reflection server at {server_spec.url} did not become healthy in time.')


def _make_reflection_server(registry: Registry, spec: ServerSpec) -> uvicorn.Server:
    """Make a reflection server for the given registry and spec.

    This is a helper function to make it easier to test the reflection server
    in isolation.

    Args:
        registry: The registry to use for the reflection server.
        spec: The spec to use for the reflection server.

    Returns:
        A uvicorn server instance.
    """
    app = create_reflection_asgi_app(registry=registry)
    # pyrefly: ignore[bad-argument-type] - Starlette app is valid ASGI app for uvicorn
    config = uvicorn.Config(app, host=spec.host, port=spec.port, loop='asyncio')
    return uvicorn.Server(config)
