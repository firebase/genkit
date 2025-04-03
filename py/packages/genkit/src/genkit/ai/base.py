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
import os
import threading
from http.server import HTTPServer

import structlog

from genkit.ai import server
from genkit.ai.plugin import Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.aio.loop import create_loop, run_async
from genkit.blocks.formats import built_in_formats
from genkit.core.environment import is_dev_environment
from genkit.core.reflection import make_reflection_server
from genkit.web.manager import find_free_port_sync

logger = structlog.get_logger(__name__)


class GenkitBase(GenkitRegistry):
    """Base class with shared infra for Genkit instances (sync and async)."""

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
        reflection_server_spec: server.ServerSpec | None = None,
    ) -> None:
        """Initialize a new Genkit instance.

        Args:
            plugins: List of plugins to initialize.
            model: Model name to use.
            reflection_server_spec: Server spec for the reflection
                server.
        """
        super().__init__()
        self.registry.default_model = model

        self.loop = create_loop()
        if is_dev_environment():
            if not reflection_server_spec:
                reflection_server_spec = server.ServerSpec(
                    scheme='http', host='127.0.0.1', port=find_free_port_sync(3100, 3999)
                )
            self.thread = threading.Thread(
                target=self.start_server,
                args=[reflection_server_spec, self.loop],
                daemon=True,
            )
            self.thread.start()
        else:
            self.thread = None
            self.loop = None

        for format in built_in_formats:
            self.define_format(format)

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

    def join(self):
        """Block until Genkit internal threads are closed. Only blocking in dev mode."""
        if is_dev_environment() and self.thread:
            self.thread.join()

    def run_async(self, async_fn):
        """Runs the provided async function as a sync/blocking function."""
        if self.loop:

            async def run():
                return await async_fn

            run_async(self.loop, run)
        else:
            asyncio.run(async_fn)
        self.join()

    def start_server(self, spec: server.ServerSpec, loop: asyncio.AbstractEventLoop) -> None:
        """Start the HTTP server for handling requests.

        Args:
            spec: Server spec for the reflection server.
            loop: Event loop to use for the server.
        """
        httpd = HTTPServer(
            (spec.host, spec.port),
            make_reflection_server(registry=self.registry, loop=loop),
        )
        # We need to write the runtime file closest to the point of starting up
        # the server to avoid race conditions with the manager's runtime
        # handler.
        runtimes_dir = os.path.join(os.getcwd(), '.genkit/runtimes')
        server.create_runtime(
            runtime_dir=runtimes_dir,
            reflection_server_spec=spec,
            at_exit_fn=os.remove,
        )
        httpd.serve_forever()
