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

import pytest

from genkit.core.action.types import ActionKind
from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore


@pytest.mark.asyncio
async def test_init_returns_retriever_and_indexer_actions():
    plugin = DevLocalVectorStore(
        name='films',
        embedder='vertexai/text-embedding-004',
    )

    actions = await plugin.init()

    assert {a.kind for a in actions} == {ActionKind.RETRIEVER, ActionKind.INDEXER}
    assert {a.name for a in actions} == {'films'}


@pytest.mark.asyncio
async def test_list_returns_action_metadata():
    plugin = DevLocalVectorStore(
        name='films',
        embedder='vertexai/text-embedding-004',
    )

    metas = await plugin.list_actions()

    assert {m.kind for m in metas} == {ActionKind.RETRIEVER, ActionKind.INDEXER}
    assert {m.name for m in metas} == {'films'}
