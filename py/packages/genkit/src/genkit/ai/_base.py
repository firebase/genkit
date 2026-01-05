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

import asyncio
import inspect
import os
import threading
from collections.abc import Coroutine
from http.server import HTTPServer
from typing import Any, TypeVar

import structlog

from genkit.aio.loop import create_loop, run_async
from genkit.blocks.formats import built_in_formats
from genkit.blocks.generate import define_generate_action
from genkit.core.action import Action
from genkit.core.environment import is_dev_environment
from genkit.core.reflection import make_reflection_server
from genkit.core.registry import ActionKind
from genkit.web.manager import find_free_port_sync

from ._plugin import Plugin, PluginV2, is_plugin_v2
from ._registry import GenkitRegistry
from ._server import ServerSpec, init_default_runtime

logger = structlog.get_logger(__name__)

T = TypeVar('T')

_instance_count = -1
_instance_lock = threading.Lock()


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
                server.
        """
        super().__init__()
        global _instance_count
        global _instance_lock
        with _instance_lock:
            _instance_count += 1
            self.id = f'{os.getpid()}-{_instance_count}'
        self._initialize_server(reflection_server_spec)
        self._initialize_registry(model, plugins)
        define_generate_action(self.registry)

    def run_main(self, coro: Coroutine[Any, Any, T] | None = None) -> T:
        """Runs the provided coroutine on an event loop.

        Args:
            coro: The coroutine to run.

        Returns:
            The result of the coroutine.
        """
        if not coro:

            async def blank_coro():
                pass

            coro = blank_coro()

        result = None
        if self._loop:

            async def run() -> T:
                return await coro

            result = run_async(self._loop, run)
        else:
            result = asyncio.run(coro)
        self._join()
        return result

    def _initialize_registry(self, model: str | None, plugins: list[Plugin] | None) -> None:
        """Initialize the registry for the Genkit sync instance.

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
                if is_plugin_v2(plugin):
                    self._initialize_v2_plugin(plugin)
                elif isinstance(plugin, Plugin):
                    plugin.initialize(ai=self)

                    def resolver(kind, name, plugin=plugin):
                        return plugin.resolve_action(self, kind, name)

                    def action_resolver(plugin=plugin):
                        if isinstance(plugin.list_actions, list):
                            return plugin.list_actions
                        else:
                            return plugin.list_actions()

                    self.registry.register_action_resolver(plugin.plugin_name(), resolver)
                    self.registry.register_list_actions_resolver(plugin.plugin_name(), action_resolver)
                else:
                    raise ValueError(f'Invalid {plugin=} provided to Genkit: must be of type `genkit.ai.Plugin` or `genkit.ai.PluginV2`')

    def _initialize_v2_plugin(self, plugin: PluginV2) -> None:
        """Register a v2 plugin by calling its methods and registering returned actions.

        Steps:
        1. Call plugin.init() to get resolved actions
        2. Register each action with automatic namespacing
        3. Set up lazy resolver for on-demand actions

        Args:
            plugin: V2 plugin instance to register.
        """
        if inspect.iscoroutinefunction(plugin.init):
            resolved_actions = asyncio.run(plugin.init())
        else:
            resolved_actions = plugin.init()

        for action in resolved_actions:
            self._register_action(action, plugin)

        def resolver(kind: ActionKind, name: str) -> None:
            """Lazy resolver for v2 plugin.

            Called when framework needs an action not returned from init().
            """
            if inspect.iscoroutinefunction(plugin.resolve):
                action = asyncio.run(plugin.resolve(kind, name))
            else:
                action = plugin.resolve(kind, name)

            if action:
                self._register_action(action, plugin)

        self.registry.register_action_resolver(plugin.name, resolver)

    def _register_action(self, action: Any, plugin: PluginV2) -> None:
        """Register a single action from a v2 plugin.

        Responsibilities:
        1. Add plugin namespace to action name (if not already present)
        2. Register action in the registry

        Args:
            action: Action instance from the plugin.
            plugin: The v2 plugin that created this action.
        """
        # Register the pre-constructed action instance and let the registry apply
        # namespacing for v2 plugins.
        self.registry.register_action_instance(action, namespace=plugin.name)


    def _initialize_server(self, reflection_server_spec: ServerSpec | None) -> None:
        """Initialize the server for the Genkit instance.

        Args:
            reflection_server_spec: Server spec for the reflection
                server.
        """
        self._loop = create_loop()
        if is_dev_environment():
            if not reflection_server_spec:
                reflection_server_spec = ServerSpec(
                    scheme='http', host='127.0.0.1', port=find_free_port_sync(3100, 3999)
                )
            self._thread = threading.Thread(
                target=self._start_server,
                args=[reflection_server_spec, self._loop],
                daemon=True,
            )
            self._thread.start()
        else:
            self._thread = None
            self._loop = None

    def _join(self):
        """Block until Genkit internal threads are closed. Only blocking in dev mode."""
        if is_dev_environment() and self._thread:
            self._thread.join()

    def _start_server(self, spec: ServerSpec, loop: asyncio.AbstractEventLoop) -> None:
        """Start the HTTP server for handling requests.

        Args:
            spec: Server spec for the reflection server.
            loop: Event loop to use for the server.
        """
        httpd = HTTPServer(
            (spec.host, spec.port),
            make_reflection_server(registry=self.registry, loop=loop, id=self.id),
        )
        # We need to write the runtime file closest to the point of starting up
        # the server to avoid race conditions with the manager's runtime
        # handler.
        init_default_runtime(spec, self.id)
        httpd.serve_forever()
