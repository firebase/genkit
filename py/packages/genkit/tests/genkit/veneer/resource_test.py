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

"""Tests for the Genkit Resource API via the Genkit class (Veneer).
This test file verifies that `ai.define_resource` works correctly, mirroring the
JS SDK's `ai.defineResource`.
"""

import asyncio

import pytest

from genkit.ai import Genkit
from genkit.core.typing import Part, TextPart


@pytest.mark.asyncio
async def test_define_resource_veneer():
    """Verifies ai.define_resource registers a resource correctly."""
    ai = Genkit(plugins=[])

    async def my_resource_fn(input, ctx):
        return {'content': [Part(root=TextPart(text=f'Content for {input.uri}'))]}

    act = ai.define_resource({'uri': 'http://example.com/foo'}, my_resource_fn)

    assert act.name == 'http://example.com/foo'
    assert act.metadata['resource']['uri'] == 'http://example.com/foo'

    # Verify lookup via global registry (contained in ai.registry)
    looked_up = ai.registry.lookup_action('resource', 'http://example.com/foo')
    assert looked_up == act

    # Verify execution
    output = await act.arun({'uri': 'http://example.com/foo'})
    assert 'Content for http://example.com/foo' in output.response['content'][0]['text']
