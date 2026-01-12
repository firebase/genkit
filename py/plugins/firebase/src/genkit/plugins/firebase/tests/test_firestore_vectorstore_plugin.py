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
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from genkit.core.action.types import ActionKind
from genkit.plugins.firebase.firestore import FirestoreVectorStore


@pytest.mark.asyncio
async def test_init_returns_retriever_action():
    plugin = FirestoreVectorStore(
        name='kb',
        firestore_client=MagicMock(),
        collection='docs',
        vector_field='embedding',
        content_field='text',
        embedder='vertexai/text-embedding-004',
        distance_measure=DistanceMeasure.COSINE,
    )

    actions = await plugin.init()

    assert len(actions) == 1
    assert actions[0].kind == ActionKind.RETRIEVER
    assert actions[0].name == 'kb'


@pytest.mark.asyncio
async def test_list_returns_metadata():
    plugin = FirestoreVectorStore(
        name='kb',
        firestore_client=MagicMock(),
        collection='docs',
        vector_field='embedding',
        content_field='text',
        embedder='vertexai/text-embedding-004',
    )

    metas = await plugin.list_actions()

    assert len(metas) == 1
    assert metas[0].kind == ActionKind.RETRIEVER
    assert metas[0].name == 'kb'
