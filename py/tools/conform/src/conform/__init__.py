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

"""Conform — parallel model conformance test runner for Genkit Python plugins.

Runs ``genkit dev:test-model`` against multiple plugins concurrently using
``asyncio``, collecting results as they arrive and displaying a live Rich
progress table.

Subcommands::

    conform run [PLUGIN...] [--all] [-j N]   Run tests in parallel
    conform check-model                      Check for missing conformance files
    conform list                             List plugins and env var status
"""

__all__: list[str] = []
