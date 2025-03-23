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

"""Asynchronous implementation of the Genkit API."""

import asyncio
from typing import Any


class GenkitAsync:
    """Asynchronous implementation of the Genkit API."""

    async def generate(self, prompt: str) -> Any:
        """Generates text based on the given prompt (async version)."""
        await asyncio.sleep(0.1)
        return {'text': f'Async response to: {prompt}'}
