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

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.google_genai.google import GoogleAI, VertexAI


@pytest.mark.asyncio
async def test_googleai_list_is_async():
    plugin = object.__new__(GoogleAI)
    plugin._client = MagicMock()
    plugin._client.models.list.return_value = []

    metas = await plugin.list_actions()
    assert isinstance(metas, list)


@pytest.mark.asyncio
async def test_vertexai_list_is_async():
    plugin = object.__new__(VertexAI)
    plugin._client = MagicMock()
    plugin._client.models.list.return_value = []

    metas = await plugin.list_actions()
    assert isinstance(metas, list)


@pytest.mark.asyncio
async def test_googleai_resolve_model_returns_action():
    plugin = object.__new__(GoogleAI)
    plugin._client = MagicMock()
    plugin._client.models.list.return_value = []

    action = await plugin.resolve(ActionKind.MODEL, 'gemini-1.5-pro')
    assert action is not None
    assert action.kind == ActionKind.MODEL
    assert action.name == 'gemini-1.5-pro'
