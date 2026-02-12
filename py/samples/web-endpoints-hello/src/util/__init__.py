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

"""Shared utility functions organized by domain.

Each submodule is independently testable and has no dependency on
Genkit, framework adapters, or application-level configuration:

- :mod:`~src.util.date` — Date/time formatting.
- :mod:`~src.util.parse` — String parsing (rate strings, comma lists).
- :mod:`~src.util.asgi` — Pure-ASGI response helpers and header extraction.
- :mod:`~src.util.hash` — Deterministic cache key generation.
"""
