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

"""Deterministic hashing and cache key generation.

Provides a stable, collision-resistant cache key function that works
with Pydantic models, dicts, and plain strings. Used by the response
cache (``src/cache.py``) to identify identical flow inputs.

Design decisions:

- **SHA-256** for collision resistance (16-char hex prefix = 64 bits).
- **Pydantic's ``model_dump_json``** for stable serialization of models.
- **``json.dumps(sort_keys=True)``** for stable dict serialization.
- **Prefix with flow name** so keys from different flows never collide.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def make_cache_key(namespace: str, input_data: BaseModel | dict[str, Any] | str) -> str:
    """Create a deterministic cache key from a namespace and input.

    Args:
        namespace: Logical namespace (e.g. flow name like
            ``"translate_text"``). Prefixed to the key so different
            namespaces never collide.
        input_data: The data to hash — a Pydantic model, dict, or
            string. Pydantic models are serialized via
            ``model_dump_json(exclude_none=True)``; dicts via
            ``json.dumps(sort_keys=True)``; strings via ``str()``.

    Returns:
        A string of the form ``"namespace:hex_prefix"`` where
        ``hex_prefix`` is the first 16 hex characters of the
        SHA-256 digest.

    Examples::

        >>> from pydantic import BaseModel
        >>> class Input(BaseModel):
        ...     text: str = 'hello'
        >>> make_cache_key('translate', Input())
        'translate:...'
        >>> make_cache_key('translate', Input()) == make_cache_key('translate', Input())
        True
        >>> make_cache_key('a', Input()) != make_cache_key('b', Input())
        True
    """
    if isinstance(input_data, BaseModel):
        serialized = input_data.model_dump_json(exclude_none=True)
    elif isinstance(input_data, dict):
        serialized = json.dumps(input_data, sort_keys=True, default=str)
    else:
        serialized = str(input_data)

    input_hash = hashlib.sha256(serialized.encode()).hexdigest()[:16]
    return f"{namespace}:{input_hash}"
