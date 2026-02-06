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

"""Tests for the Dynamic Action Provider (DAP) module.

This module contains comprehensive tests for the DAP functionality,
ensuring parity with the JavaScript implementation in:
    js/core/tests/dynamic-action-provider_test.ts

Test Coverage
=============

┌─────────────────────────────────────────────────────────────────────────────┐
│ Test Case                     │ Description                                  │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ test_gets_specific_action     │ Get a specific action by type and name       │
│ test_lists_action_metadata    │ List metadata with wildcard pattern          │
│ test_caches_actions           │ Verify caching prevents redundant fetches    │
│ test_invalidates_cache        │ Cache invalidation forces fresh fetch        │
│ test_respects_cache_ttl       │ TTL expiration triggers refresh              │
│ test_lists_actions_with_prefix│ Prefix matching for action names             │
│ test_lists_actions_exact_match│ Exact name matching                          │
│ test_gets_action_metadata_rec │ Reflection API metadata record format        │
│ test_handles_concurrent_reqs  │ Concurrent requests share single fetch       │
│ test_handles_fetch_errors     │ Error recovery and cache invalidation        │
│ test_identifies_dap           │ Type identification helper                   │
│ test_transform_dap_value      │ Value to metadata transformation             │
└───────────────────────────────┴──────────────────────────────────────────────┘
"""

import asyncio

import pytest

from genkit.blocks.dap import (
    DapCacheConfig,
    DapConfig,
    DapValue,
    DynamicActionProvider,
    define_dynamic_action_provider,
    is_dynamic_action_provider,
    transform_dap_value,
)
from genkit.core.action import Action
from genkit.core.action.types import ActionKind
from genkit.core.error import GenkitError
from genkit.core.registry import Registry, parse_registry_key


@pytest.fixture
def registry() -> Registry:
    """Create a fresh registry for each test."""
    return Registry()


@pytest.fixture
def tool1(registry: Registry) -> Action:
    """Create tool1 action for testing."""

    async def tool1_fn(input: str) -> str:
        return 'tool1'

    return registry.register_action(
        name='tool1',
        kind=ActionKind.TOOL,
        fn=tool1_fn,
        metadata={'name': 'tool1'},
    )


@pytest.fixture
def tool2(registry: Registry) -> Action:
    """Create tool2 action for testing."""

    async def tool2_fn(input: str) -> str:
        return 'tool2'

    return registry.register_action(
        name='tool2',
        kind=ActionKind.TOOL,
        fn=tool2_fn,
        metadata={'name': 'tool2'},
    )


@pytest.fixture
def other_tool(registry: Registry) -> Action:
    """Create other-tool action for testing prefix matching."""

    async def other_tool_fn(input: str) -> str:
        return 'other'

    return registry.register_action(
        name='other-tool',
        kind=ActionKind.TOOL,
        fn=other_tool_fn,
        metadata={'name': 'other-tool'},
    )


@pytest.mark.asyncio
async def test_gets_specific_action(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test getting a specific action by type and name.

    Corresponds to JS test: 'gets a specific action'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    action = await dap.get_action('tool', 'tool1')
    assert action is tool1
    assert call_count == 1


@pytest.mark.asyncio
async def test_lists_action_metadata(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test listing action metadata with wildcard.

    Corresponds to JS test: 'lists action metadata'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    metadata = await dap.list_action_metadata('tool', '*')
    assert len(metadata) == 2
    # New API includes name/description in returned metadata
    assert metadata[0].get('name') == 'tool1'
    assert metadata[1].get('name') == 'tool2'
    assert call_count == 1


@pytest.mark.asyncio
async def test_caches_actions(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that actions are cached across multiple calls.

    Corresponds to JS test: 'caches the actions'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    action = await dap.get_action('tool', 'tool1')
    assert action is tool1
    assert call_count == 1

    # This should be cached
    action = await dap.get_action('tool', 'tool2')
    assert action is tool2
    assert call_count == 1

    metadata = await dap.list_action_metadata('tool', '*')
    assert len(metadata) == 2
    assert call_count == 1


@pytest.mark.asyncio
async def test_invalidates_cache(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that cache invalidation forces a fresh fetch.

    Corresponds to JS test: 'invalidates the cache'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    await dap.get_action('tool', 'tool1')
    assert call_count == 1

    dap.invalidate_cache()

    await dap.get_action('tool', 'tool2')
    assert call_count == 2


@pytest.mark.asyncio
async def test_respects_cache_ttl(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that cache respects TTL configuration.

    Corresponds to JS test: 'respects cache ttl'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    config = DapConfig(name='my-dap', cache_config=DapCacheConfig(ttl_millis=10))
    dap = define_dynamic_action_provider(registry, config, dap_fn)

    await dap.get_action('tool', 'tool1')
    assert call_count == 1

    # Wait for TTL to expire
    await asyncio.sleep(0.025)  # 25ms > 10ms TTL

    await dap.get_action('tool', 'tool2')
    assert call_count == 2


@pytest.mark.asyncio
async def test_lists_actions_with_prefix(registry: Registry, tool1: Action, tool2: Action, other_tool: Action) -> None:
    """Test listing actions with prefix pattern matching.

    Corresponds to JS test: 'lists actions with prefix'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2, other_tool]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    metadata = await dap.list_action_metadata('tool', 'tool*')
    assert len(metadata) == 2
    # New API includes name/description in returned metadata
    assert metadata[0].get('name') == 'tool1'
    assert metadata[1].get('name') == 'tool2'
    assert call_count == 1


@pytest.mark.asyncio
async def test_lists_actions_exact_match(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test listing actions with exact name matching.

    Corresponds to JS test: 'lists actions with exact match'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    metadata = await dap.list_action_metadata('tool', 'tool1')
    assert len(metadata) == 1
    # New API includes name/description in returned metadata
    assert metadata[0].get('name') == 'tool1'
    assert call_count == 1


@pytest.mark.asyncio
async def test_gets_action_metadata_record(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test getting action metadata record for reflection API.

    Corresponds to JS test: 'gets action metadata record'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {
            'tool': [tool1, tool2],
            'flow': [tool1],
        }

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    record = await dap.get_action_metadata_record('dap/my-dap')
    assert 'dap/my-dap:tool/tool1' in record
    assert 'dap/my-dap:tool/tool2' in record
    assert 'dap/my-dap:flow/tool1' in record
    # New API returns dict with name/description included
    assert record['dap/my-dap:tool/tool1'].get('name') == 'tool1'
    assert record['dap/my-dap:tool/tool2'].get('name') == 'tool2'
    assert record['dap/my-dap:flow/tool1'].get('name') == 'tool1'
    assert call_count == 1


@pytest.mark.asyncio
async def test_handles_concurrent_requests(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that concurrent requests share a single fetch operation.

    Corresponds to JS test: 'handles concurrent requests'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # Simulate async work
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    # Run two requests concurrently
    results = await asyncio.gather(
        dap.list_action_metadata('tool', '*'),
        dap.list_action_metadata('tool', '*'),
    )

    metadata1, metadata2 = results
    assert len(metadata1) == 2
    assert len(metadata2) == 2
    # New API includes name/description in returned metadata
    assert metadata1[0].get('name') == 'tool1'
    assert metadata2[0].get('name') == 'tool1'
    # Only one fetch should have occurred
    assert call_count == 1


@pytest.mark.asyncio
async def test_handles_fetch_errors(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that DAP raises GenkitError on fetch failure."""
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError('Fetch failed')
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    # First call should raise (wrapped in GenkitError by action tracing)
    with pytest.raises(GenkitError):
        await dap.list_action_metadata('tool', '*')
    assert call_count == 1

    # Second call should succeed (cache was invalidated)
    metadata = await dap.list_action_metadata('tool', '*')
    assert len(metadata) == 2
    assert call_count == 2


@pytest.mark.asyncio
async def test_identifies_dap(registry: Registry, tool1: Action) -> None:
    """Test the is_dynamic_action_provider helper function.

    Corresponds to JS test: 'identifies dynamic action providers'
    """

    async def dap_fn() -> DapValue:
        return {}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)
    assert is_dynamic_action_provider(dap) is True

    # Regular action should not be identified as DAP
    assert is_dynamic_action_provider(tool1) is False


def test_transform_dap_value(tool1: Action, tool2: Action) -> None:
    """Test the transform_dap_value utility function.

    Updated for PR #4050 parity: returns flat list instead of grouped dict.
    """
    value: DapValue = {'tool': [tool1, tool2]}

    metadata = transform_dap_value(value)

    # New API returns flat list of action metadata
    assert isinstance(metadata, list)
    assert len(metadata) == 2
    assert metadata[0].get('name') == 'tool1'
    assert metadata[1].get('name') == 'tool2'


def test_dap_config_string_normalization(registry: Registry) -> None:
    """Test that string config is normalized to DapConfig.

    The define_dynamic_action_provider should accept either a string
    or a DapConfig object.
    """

    async def dap_fn() -> DapValue:
        return {}

    # String config
    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)
    assert isinstance(dap, DynamicActionProvider)
    assert dap.config.name == 'my-dap'


def test_dap_config_with_full_options(registry: Registry) -> None:
    """Test DapConfig with all options specified."""

    async def dap_fn() -> DapValue:
        return {}

    config = DapConfig(
        name='full-config-dap',
        description='A DAP with all options',
        cache_config=DapCacheConfig(ttl_millis=5000),
        metadata={'custom': 'value'},
    )

    dap = define_dynamic_action_provider(registry, config, dap_fn)
    assert dap.config.name == 'full-config-dap'
    assert dap.config.description == 'A DAP with all options'
    assert dap.config.cache_config is not None
    assert dap.config.cache_config.ttl_millis == 5000
    assert dap.config.metadata == {'custom': 'value'}


@pytest.mark.asyncio
async def test_get_action_returns_none_for_unknown_type(registry: Registry, tool1: Action) -> None:
    """Test that get_action returns None for unknown action types."""

    async def dap_fn() -> DapValue:
        return {'tool': [tool1]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    action = await dap.get_action('unknown-type', 'tool1')
    assert action is None


@pytest.mark.asyncio
async def test_get_action_returns_none_for_unknown_name(registry: Registry, tool1: Action) -> None:
    """Test that get_action returns None for unknown action names."""

    async def dap_fn() -> DapValue:
        return {'tool': [tool1]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    action = await dap.get_action('tool', 'unknown-name')
    assert action is None


@pytest.mark.asyncio
async def test_list_action_metadata_returns_empty_for_unknown_type(registry: Registry, tool1: Action) -> None:
    """Test that list_action_metadata returns empty list for unknown types."""

    async def dap_fn() -> DapValue:
        return {'tool': [tool1]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    metadata = await dap.list_action_metadata('unknown-type', '*')
    assert metadata == []


@pytest.mark.asyncio
async def test_negative_ttl_disables_caching(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that negative TTL disables caching (always fetch fresh)."""
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    config = DapConfig(name='my-dap', cache_config=DapCacheConfig(ttl_millis=-1))
    dap = define_dynamic_action_provider(registry, config, dap_fn)

    await dap.get_action('tool', 'tool1')
    assert call_count == 1

    # With negative TTL, this should trigger another fetch
    await dap.get_action('tool', 'tool2')
    assert call_count == 2


@pytest.mark.asyncio
async def test_zero_ttl_uses_default(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that zero TTL uses the default (3000ms)."""
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    config = DapConfig(name='my-dap', cache_config=DapCacheConfig(ttl_millis=0))
    dap = define_dynamic_action_provider(registry, config, dap_fn)

    await dap.get_action('tool', 'tool1')
    assert call_count == 1

    # With default TTL (3s), this should still be cached
    await dap.get_action('tool', 'tool2')
    assert call_count == 1


@pytest.mark.asyncio
async def test_get_action_metadata_record_raises_on_missing_name(registry: Registry) -> None:
    """Test that get_action_metadata_record raises error when action has no name."""

    async def nameless_fn(input: str) -> str:
        return 'nameless'

    nameless_action = registry.register_action(
        name='nameless',
        kind=ActionKind.TOOL,
        fn=nameless_fn,
        metadata={},  # No 'name' in metadata
    )
    # Clear the name attribute to simulate a nameless action
    nameless_action._name = ''

    async def dap_fn() -> DapValue:
        return {'tool': [nameless_action]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    with pytest.raises(ValueError, match='name required'):
        await dap.get_action_metadata_record('dap/my-dap')


@pytest.mark.asyncio
async def test_parse_registry_key_standard_format() -> None:
    """Test parsing standard registry keys."""
    # Standard model key
    parsed = parse_registry_key('/model/googleai/gemini-2.0-flash')
    assert parsed is not None
    assert parsed.action_type == 'model'
    assert parsed.plugin_name == 'googleai'
    assert parsed.action_name == 'gemini-2.0-flash'
    assert parsed.dynamic_action_host is None

    # Util key (short format)
    parsed = parse_registry_key('/util/generate')
    assert parsed is not None
    assert parsed.action_type == 'util'
    assert parsed.action_name == 'generate'
    assert parsed.plugin_name is None

    # Invalid key
    parsed = parse_registry_key('invalid')
    assert parsed is None


@pytest.mark.asyncio
async def test_parse_registry_key_dap_format() -> None:
    """Test parsing DAP-style registry keys."""
    # DAP key with action type and name
    parsed = parse_registry_key('/dynamic-action-provider/mcp-host:tool/my-tool')
    assert parsed is not None
    assert parsed.dynamic_action_host == 'mcp-host'
    assert parsed.action_type == 'tool'
    assert parsed.action_name == 'my-tool'

    # DAP key without action type (just host)
    parsed = parse_registry_key('/dynamic-action-provider/mcp-host')
    assert parsed is not None
    assert parsed.action_type == 'dynamic-action-provider'
    assert parsed.action_name == 'mcp-host'


@pytest.mark.asyncio
async def test_list_resolvable_actions_includes_dap(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that list_resolvable_actions includes DAP-provided actions."""
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    define_dynamic_action_provider(registry, 'test-dap', dap_fn)

    # Get resolvable actions
    metas = await registry.list_resolvable_actions()

    # Should include the DAP itself and the tools it provides (with full keys)
    names = [m.name for m in metas]
    assert 'test-dap' in names  # The DAP action
    assert '/dynamic-action-provider/test-dap:tool/tool1' in names  # DAP-provided tool
    assert '/dynamic-action-provider/test-dap:tool/tool2' in names  # DAP-provided tool


@pytest.mark.asyncio
async def test_runs_action_with_transformed_metadata(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that the DAP action returns transformed metadata when run.

    Corresponds to JS test: 'runs the action with transformed metadata when fetching'
    """

    async def dap_fn() -> DapValue:
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    # Fetch the DAP value through the cache (which runs the action)
    await dap._cache.get_or_fetch()

    # Run the action directly and check the result is transformed metadata
    result = await dap.action.arun(None)
    metadata_list = result.response

    # Should return transformed metadata (list of ActionMetadata-like dicts)
    assert len(metadata_list) == 2
    names = [m['name'] for m in metadata_list]
    assert 'tool1' in names
    assert 'tool2' in names


@pytest.mark.asyncio
async def test_skips_trace_when_requested(registry: Registry, tool1: Action, tool2: Action) -> None:
    """Test that skipTrace parameter skips creating a trace.

    Corresponds to JS test: 'skips trace when requested'
    """
    call_count = 0

    async def dap_fn() -> DapValue:
        nonlocal call_count
        call_count += 1
        return {'tool': [tool1, tool2]}

    dap = define_dynamic_action_provider(registry, 'my-dap', dap_fn)

    # Fetch with skip_trace=True should call the dap_fn directly (not via action.run)
    await dap._cache.get_or_fetch(skip_trace=True)
    assert call_count == 1

    # Invalidate cache
    dap.invalidate_cache()

    # Fetch without skip_trace should also work (calls via action.run which calls dap_fn)
    await dap._cache.get_or_fetch(skip_trace=False)
    assert call_count == 2
