# Copyright 2026 Google LLC
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

import os
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from fakes import mock_mcp_modules

mock_mcp_modules()

import unittest
from unittest.mock import patch

from genkit.ai import Genkit
from genkit.core.action.types import ActionKind

# Now import plugin
from genkit.plugins.mcp import McpClient, McpHost, McpServerConfig, create_mcp_host


class TestMcpHost(unittest.IsolatedAsyncioTestCase):
    async def test_connect_and_register(self):
        # Setup configs
        config1 = McpServerConfig(command='echo')
        config2 = McpServerConfig(url='http://localhost:8000')

        host = create_mcp_host({'server1': config1, 'server2': config2})

        # Mock clients within host
        with patch('genkit.plugins.mcp.client.client.McpClient.connect', new_callable=AsyncMock) as mock_connect:
            await host.start()
            self.assertEqual(mock_connect.call_count, 2)

        # Mock session for registration
        host.clients['server1'].session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = 'tool1'
        host.clients['server1'].session.list_tools.return_value.tools = [mock_tool]

        ai = MagicMock(spec=Genkit)
        ai.registry = MagicMock()

        await host.register_tools(ai)

        # Verify tool registration
        ai.registry.register_action.assert_called()
        call_args = ai.registry.register_action.call_args[1]
        self.assertIn('server1/tool1', call_args['name'])
