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

"""Unittest for VertexAIVectorSearch plugin."""

from unittest.mock import MagicMock

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.vertex_ai.vector_search import VertexAIVectorSearch


@pytest.mark.asyncio
async def test_init_plugin_returns_retriever_action():
    """PluginV2 init should return the vector-search retriever action."""
    plugin = VertexAIVectorSearch(
        retriever=MagicMock(),
        embedder='embedder',
    )

    actions = await plugin.init()

    assert len(actions) == 1
    assert actions[0].kind == ActionKind.RETRIEVER
    assert actions[0].name == 'vertexAIVectorSearch'
