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

from collections.abc import Coroutine
from typing import Any, TypeVar

import anyio
import structlog
import uvicorn

from genkit.aio.loop import run_loop
from genkit.blocks.formats import built_in_formats
from genkit.core.environment import is_dev_environment
from genkit.core.reflection import create_reflection_asgi_app
from genkit.web.manager import find_free_port_sync

from ._plugin import Plugin
from ._registry import GenkitRegistry
from ._runtime import RuntimeManager
from ._server import ServerSpec

logger = structlog.get_logger(__name__)

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
        self._reflection_server_spec = reflection_server_spec
        self._initialize_registry(model, plugins)

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
                if isinstance(plugin, Plugin):
                    plugin.initialize(ai=self)

                    def resolver(kind, name, plugin=plugin):
                        return plugin.resolve_action(self, kind, name)

                    self.registry.register_action_resolver(plugin.plugin_name(), resolver)
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

        async def dev_runner():
            """Internal async function to run tasks using AnyIO TaskGroup."""
            user_result: T | None = None
            user_task_finished_event = anyio.Event()

            async def run_user_coro_wrapper():
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

            reflection_server = _make_reflection_server(self.registry, spec)

            try:
                async with RuntimeManager(spec):
                    # We use anyio.TaskGroup because it is compatible with
                    # asyncio's event loop and works with Python 3.10
                    # (asyncio.TaskGroup was added in 3.11, and we can switch to
                    # that when we drop support for 3.10).
                    async with anyio.create_task_group() as tg:
                        # Start reflection server in the background.
                        tg.start_soon(reflection_server.serve, name='genkit-reflection-server')
                        await logger.ainfo(f'Started Genkit reflection server at {spec.url}')

                        # Start the (potentially short-lived) user coroutine wrapper
                        tg.start_soon(run_user_coro_wrapper, name='genkit-user-coroutine')
                        await logger.ainfo('Started Genkit user coroutine')

                        # Block here until the task group is canceled (e.g. Ctrl+C)
                        # or a task raises an unhandled exception. It should not
                        # exit just because the user coroutine finishes.

            except anyio.get_cancelled_exc_class():
                logger.info('Development server task group cancelled (e.g., Ctrl+C).')
                raise
            except Exception as e:
                logger.exception(e)
                raise

            # After the TaskGroup finishes (error or cancelation).
            if user_task_finished_event.is_set():
                await logger.adebug('User coroutine finished before TaskGroup exit.')
                return user_result
            else:
                await logger.adebug('User coroutine did not finish before TaskGroup exit.')
                return None

        return anyio.run(dev_runner)


def _make_reflection_server(registry: GenkitRegistry, spec: ServerSpec) -> uvicorn.Server:
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
    config = uvicorn.Config(app, host=spec.host, port=spec.port, loop='asyncio')
    return uvicorn.Server(config)
