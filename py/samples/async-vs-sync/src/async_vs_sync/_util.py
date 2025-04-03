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

"""Utility functions for the async-vs-sync sample."""

import asyncio

from genkit.web.manager import Server, ServerManager


async def add_server_after(mgr: ServerManager, server: Server, delay: float) -> None:
    """Add a server to the servers manager after a delay.

    Args:
        mgr: The servers manager.
        server: The server to add.
        delay: The delay in seconds before adding the server.

    Returns:
        None
    """
    await asyncio.sleep(delay)
    await mgr.queue_server(server)
