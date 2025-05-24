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

from genkit.ai import Genkit
from genkit.plugins.vertex_ai import VertexAIVectorSearch


def test_initialize_plugin():
    """Test plugin initialization."""
    plugin = VertexAIVectorSearch(
        retriever=MagicMock(),
        embedder='embedder',
    )

    result = plugin.initialize(ai=MagicMock(spec=Genkit))

    assert result is not None
