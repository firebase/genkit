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

"""Tests for the action module."""

from genkit.blocks.embedding import embedder_action_metadata
from genkit.core.action import ActionMetadata


def test_embedder_action_metadata():
    """Test for embedder_action_metadata."""
    action_metadata = embedder_action_metadata(
        name='test_model',
        info={'label': 'test_label'},
        config_schema=None,
    )

    assert isinstance(action_metadata, ActionMetadata)
    assert action_metadata.input_json_schema is not None
    assert action_metadata.output_json_schema is not None
    assert action_metadata.metadata == {'embedder': {'customOptions': None, 'label': 'test_label'}}
