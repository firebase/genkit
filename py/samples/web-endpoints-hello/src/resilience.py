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

"""Shared resilience singletons — cache and circuit breaker.

This module holds the global :class:`FlowCache` and
:class:`CircuitBreaker` instances that are configured at startup
(in ``main.py``) and imported by ``flows.py`` and route handlers.

The instances are set to ``None`` initially. ``main()`` replaces them
with configured instances before any request can arrive. If a flow is
called before ``main()`` runs (e.g. during testing), the ``None``
values signal to the flow that resilience wrappers should be skipped.

Usage in flows::

    from .resilience import flow_cache, llm_breaker


    async def my_flow(input):
        if flow_cache is not None:
            return await flow_cache.get_or_call("my_flow", input, lambda: _do_work(input))
        return await _do_work(input)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cache import FlowCache
    from .circuit_breaker import CircuitBreaker

flow_cache: FlowCache | None = None
"""Global response cache — set by ``main()`` at startup."""

llm_breaker: CircuitBreaker | None = None
"""Global LLM circuit breaker — set by ``main()`` at startup."""
