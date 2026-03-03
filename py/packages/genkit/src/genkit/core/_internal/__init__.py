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

"""Internal utilities for Genkit core.

This package contains internal implementation details that are not part of the
public API. These modules may change without notice between releases.
"""

from ._aio import (
    Channel,
    create_loop,
    ensure_async,
    iter_over_async,
    run_async,
    run_loop,
)

__all__ = [
    'Channel',
    'create_loop',
    'ensure_async',
    'iter_over_async',
    'run_async',
    'run_loop',
]
