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

"""Dynamic Action Provider (DAP) support for Genkit."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from genkit._core._action import (
    GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR,
    Action,
    ActionKind,
)
from genkit._core._error import GenkitError
from genkit._core._registry import Registry

ActionMetadataLike = Mapping[str, object]
DapValue = dict[str, list[Action[Any, Any]]]
DapFn = Callable[[], Awaitable[DapValue]]

# Default cache TTL in milliseconds
_DEFAULT_CACHE_TTL_MS = 3000


class DynamicActionProvider:
    """Lazily resolves actions from an external source with TTL caching."""

    def __init__(
        self,
        action: Action[Any, Any],
        dap_fn: DapFn,
        cache_ttl_millis: int | None = None,
    ) -> None:
        self.action = action
        self._dap_fn = dap_fn
        self._value: DapValue | None = None
        self._expires_at: float | None = None
        self._fetch_task: asyncio.Task[DapValue] | None = None
        self._ttl_millis = (
            _DEFAULT_CACHE_TTL_MS if cache_ttl_millis is None or cache_ttl_millis == 0 else cache_ttl_millis
        )

    def set_value(self, value: DapValue) -> None:
        """Update the cached value and reset expiry. Called by the action body."""
        self._value = value
        self._expires_at = time.time() * 1000 + self._ttl_millis

    def invalidate_cache(self) -> None:
        self._value = None
        self._expires_at = None

    async def _get_or_fetch(self, skip_trace: bool = False) -> DapValue:
        """Get cached value or fetch fresh data, coalescing concurrent fetches."""
        is_stale = (
            self._value is None
            or self._expires_at is None
            or self._ttl_millis < 0
            or time.time() * 1000 > self._expires_at
        )
        if not is_stale and self._value is not None:
            return self._value

        if self._fetch_task is not None:
            return await self._fetch_task

        self._fetch_task = asyncio.create_task(self._do_fetch(skip_trace))
        try:
            return await self._fetch_task
        finally:
            self._fetch_task = None

    async def _do_fetch(self, skip_trace: bool) -> DapValue:
        try:
            if skip_trace:
                # Bypass the action (and its trace span) for reflection/devtools
                # listing, which would otherwise flood traces.
                value = await self._dap_fn()
                self.set_value(value)
                return value
            else:
                # Run through the action so the fetch is wrapped in a trace span.
                # The action body calls _dap_fn() and set_value().
                try:
                    await self.action.run()
                except GenkitError as e:
                    raise e.__cause__ or e
                if self._value is None:
                    raise ValueError('DAP value undefined after action run')
                return self._value
        except Exception:
            self.invalidate_cache()
            raise

    async def get_action(self, action_type: str, action_name: str) -> Action[Any, Any] | None:
        result = await self._get_or_fetch()
        for action in result.get(action_type, []):
            if action.name == action_name:
                return action
        return None

    async def list_action_metadata(self, action_type: str, action_name: str) -> list[ActionMetadataLike]:
        """List metadata matching pattern: '*'=all, 'prefix*'=prefix match, else exact."""
        result = await self._get_or_fetch()
        actions = result.get(action_type, [])
        if not actions:
            return []

        metadata_list: list[ActionMetadataLike] = [action.metadata or {} for action in actions]

        if action_name == '*':
            return metadata_list
        if action_name.endswith('*'):
            prefix = action_name[:-1]
            return [m for m in metadata_list if str(m.get('name', '')).startswith(prefix)]
        return [m for m in metadata_list if m.get('name') == action_name]

    async def get_action_metadata_record(self, dap_prefix: str) -> dict[str, ActionMetadataLike]:
        """Get all actions as metadata record for reflection API."""
        result = await self._get_or_fetch(skip_trace=True)
        dap_actions: dict[str, ActionMetadataLike] = {}
        for action_type, actions in result.items():
            for action in actions:
                if not action.name:
                    raise ValueError(f'Invalid metadata from {dap_prefix} - name required')
                dap_actions[f'{dap_prefix}:{action_type}/{action.name}'] = action.metadata or {}
        return dap_actions


def is_dynamic_action_provider(obj: object) -> bool:
    if isinstance(obj, DynamicActionProvider):
        return True
    metadata = getattr(obj, 'metadata', None)
    return isinstance(metadata, dict) and metadata.get('type') == 'dynamic-action-provider'


def define_dynamic_action_provider(
    registry: Registry,
    name: str,
    fn: DapFn,
    *,
    description: str | None = None,
    cache_ttl_millis: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> DynamicActionProvider:
    """Define and register a Dynamic Action Provider for lazy action resolution."""

    # Filled in immediately after construction; the closure reads it when run() fires.
    _dap: DynamicActionProvider | None = None

    async def dap_action(input: None) -> None:
        value = await fn()
        assert _dap is not None
        _dap.set_value(value)

    action = registry.register_action(
        name=name,
        kind=ActionKind.DYNAMIC_ACTION_PROVIDER,
        description=description,
        fn=dap_action,
        metadata={**(metadata or {}), 'type': 'dynamic-action-provider'},
    )

    dap = DynamicActionProvider(action, fn, cache_ttl_millis)
    _dap = dap
    setattr(action, GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR, dap)
    return dap
