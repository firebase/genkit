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

"""Base/shared implementation for Genkit user-facing API."""

import os
import threading

import structlog
import uvicorn

from genkit.ai import server
from genkit.ai.plugin import Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.ai.server import create_runtime
from genkit.blocks.formats import built_in_formats
from genkit.core.environment import is_dev_environment
from genkit.core.reflection import create_reflection_asgi_app
from genkit.web.manager import ServerManagerProtocol

from ._reflection import make_managed_reflection_server, make_reflection_server_spec

logger = structlog.get_logger(__name__)


class GenkitBase(GenkitRegistry):
    """Base class with shared infra for Genkit instances (sync and async)."""

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
        reflection_server_spec: server.ServerSpec | None = None,
        manager: ServerManagerProtocol | None = None,
    ) -> None:
        """Initialize a new Genkit instance.

        Args:
            plugins: List of plugins to initialize.
            model: Model name to use.
            reflection_server_spec: Server spec for the reflection
                server.
            manager: Server manager to use.
        """
        super().__init__()
        self.registry.default_model = model
        self._reflection_server_spec = make_reflection_server_spec(reflection_server_spec)
        self._user_provided_manager = manager is not None
        self._manager = manager

        self._start_reflection_server()
        self._initialize_formats()
        self._initialize_plugins(plugins)

    # TODO: Remove this once we've migrated all the code to the new implementation.
    def join(self):
        """Block until Genkit internal threads are closed. Only blocking in dev mode."""
        pass

    def _initialize_formats(self) -> None:
        """Initialize the formats for the Genkit instance."""
        for format in built_in_formats:
            self.define_format(format)

    def _initialize_plugins(self, plugins: list[Plugin] | None) -> None:
        """Initialize the plugins for the Genkit instance."""
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
                    raise ValueError(f'Invalid {plugin=} provided to Genkit: must be of type `genkit.ai.plugin.Plugin`')

    def _start_reflection_server(self) -> None:
        """Start the reflection server.

        In development mode, this will start the reflection server either using
        the provided manager or in a background thread.
        """
        if not is_dev_environment():
            logger.debug('[🟢] Not in dev environment, skipping automatic dev services start.')
            return

        logger.info('[🟠] Creating reflection server runtime...')
        runtimes_dir = os.path.join(os.getcwd(), '.genkit/runtimes')
        create_runtime(
            runtime_dir=runtimes_dir,
            reflection_server_spec=self._reflection_server_spec,
            at_exit_fn=os.remove,
        )
        logger.info('[🟠] Reflection server runtime created.')

        if self._manager is not None:
            # User provided a server manager, queue the server.
            logger.debug('[🟠] Queueing reflection server on provided server manager.')
            self._manager.queue_server(make_managed_reflection_server(self.registry, self._reflection_server_spec))
        else:
            # No server manager provided: start the dev server background
            # thread.  Note: We don't store the thread reference here, assuming
            # its only purpose is to keep the process alive via non-daemon
            # status.
            reflection_server_thread = threading.Thread(
                target=self._run_reflection_server_thread,
                name='genkit-reflection-server-thread',
                daemon=False,  # Non-daemon to block main thread exit.
            )
            reflection_server_thread.start()
            logger.info(f"[🟠] Reflection server thread '{reflection_server_thread.name}' started.")

    def _run_reflection_server_thread(self) -> None:
        """Target function to run the server in a dedicated thread using uvicorn directly.

        This function is used to start the development server in a separate thread.
        It runs uvicorn directly with the server configuration.

        Returns:
            None
        """
        logger.info('[🟠] Starting development server thread.')
        try:
            app = create_reflection_asgi_app(registry=self.registry)
            uvicorn.run(
                app,
                host=self._reflection_server_spec.host,
                port=self._reflection_server_spec.port,
                log_level='info',
            )
            logger.info('[🟠] Development server finished running.')
        except Exception:
            logger.exception('[🟠] Error occurred during development server execution.')
        finally:
            logger.info('[🟠] Development server thread finished.')
