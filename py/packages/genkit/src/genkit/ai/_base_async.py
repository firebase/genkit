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

import asyncio
import signal
import socket
import threading
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
from genkit.core.reflection import create_reflection_asgi_app
from genkit.core.registry import Registry

from ._registry import GenkitRegistry
from ._runtime import RuntimeManager
from ._server import ServerSpec

logger = get_logger(__name__)

T = TypeVar('T')


class _ReflectionServer(uvicorn.Server):
    """A uvicorn.Server subclass that signals startup completion via a threading.Event."""

    def __init__(self, config: uvicorn.Config, ready: threading.Event) -> None:
        """Initialize the server with a ready event to set on startup."""
        super().__init__(config)
        self._ready = ready

    async def startup(self, sockets: list | None = None) -> None:
        """Override to set the ready event once uvicorn finishes binding."""
        try:
            await super().startup(sockets=sockets)
        finally:
            self._ready.set()


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
        self._reflection_ready = threading.Event()
        self._initialize_registry(model, plugins)
        # Ensure the default generate action is registered for async usage.
        define_generate_action(self.registry)
        # In dev mode, start the reflection server immediately in a background
        # daemon thread so it's available regardless of which web framework (or
        # none) the user chooses.
        if is_dev_environment():
            self._start_reflection_background()

    def _start_reflection_background(self) -> None:
        """Start the Dev UI reflection server in a background daemon thread.

        The thread owns its own asyncio event loop so it never conflicts with
        the main thread's loop (whether that's uvicorn, FastAPI, or none).
        Sets ``self._reflection_ready`` once the server is listening.
        """

        def _thread_main() -> None:
            async def _run() -> None:
                sockets: list[socket.socket] | None = None
                spec = self._reflection_server_spec
                if spec is None:
                    # Bind to port 0 to let the OS choose an available port and
                    # pass the socket to uvicorn to avoid a check-then-bind race.
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind(('127.0.0.1', 0))
                    sock.listen(2048)
                    host, port = sock.getsockname()
                    spec = ServerSpec(scheme='http', host=host, port=port)
                    self._reflection_server_spec = spec
                    sockets = [sock]

                server = _make_reflection_server(self.registry, spec, ready=self._reflection_ready)
                async with RuntimeManager(spec, lazy_write=True) as runtime_manager:
                    server_task = asyncio.create_task(server.serve(sockets=sockets))

                    # _ReflectionServer.startup() sets _reflection_ready once uvicorn binds.
                    # Use asyncio.to_thread so we don't block the event loop.
                    await asyncio.to_thread(self._reflection_ready.wait)

                    if server.should_exit:
                        logger.warning(f'Reflection server at {spec.url} failed to start.')
                        return

                    runtime_manager.write_runtime_file()
                    await logger.ainfo(f'Genkit Dev UI reflection server running at {spec.url}')

                    # Keep running until the process exits (daemon thread).
                    await server_task

            asyncio.run(_run())

        t = threading.Thread(target=_thread_main, daemon=True, name='genkit-reflection-server')
        t.start()

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

    def run_main(self, coro: Coroutine[Any, Any, T]) -> T | None:
        """Run the user's main coroutine.

        In development mode (`GENKIT_ENV=dev`), this runs the user's coroutine
        then blocks until Ctrl+C or SIGTERM, keeping the background reflection
        server (started in ``__init__``) alive for the Dev UI.

        In production mode, this simply runs the user's coroutine to completion
        using ``uvloop.run()`` for performance if available, otherwise
        ``asyncio.run()``.

        Args:
            coro: The main coroutine provided by the user.

        Returns:
            The result of the user's coroutine, or None on graceful shutdown.
        """
        if not is_dev_environment():
            logger.info('Running in production mode.')
            return run_loop(coro)

        logger.info('Running in development mode.')

        async def dev_runner() -> T | None:
            user_result: T | None = None
            try:
                user_result = await coro
                logger.debug('User coroutine completed successfully.')
            except Exception:
                logger.exception('User coroutine failed')

            # Block until Ctrl+C (SIGINT handled by anyio) or SIGTERM, keeping
            # the daemon reflection thread alive.
            logger.info('Script done — Dev UI running. Press Ctrl+C to stop.')
            try:
                async with anyio.create_task_group() as tg:

                    async def _handle_sigterm(tg_: anyio.abc.TaskGroup) -> None:  # type: ignore[name-defined]
                        with anyio.open_signal_receiver(signal.SIGTERM) as sigs:
                            async for _ in sigs:
                                tg_.cancel_scope.cancel()
                                return

                    tg.start_soon(_handle_sigterm, tg)
                    await anyio.sleep_forever()
            except anyio.get_cancelled_exc_class():
                pass

            logger.info('Dev UI server stopped.')
            return user_result

        return anyio.run(dev_runner)


def _make_reflection_server(registry: Registry, spec: ServerSpec, ready: threading.Event) -> _ReflectionServer:
    """Make a reflection server for the given registry and spec.

    This is a helper function to make it easier to test the reflection server
    in isolation.

    Args:
        registry: The registry to use for the reflection server.
        spec: The spec to use for the reflection server.
        ready: threading.Event to set once uvicorn finishes binding.

    Returns:
        A uvicorn server instance.
    """
    app = create_reflection_asgi_app(registry=registry)
    # pyrefly: ignore[bad-argument-type] - Starlette app is valid ASGI app for uvicorn
    config = uvicorn.Config(app, host=spec.host, port=spec.port, loop='asyncio')
    return _ReflectionServer(config, ready=ready)
