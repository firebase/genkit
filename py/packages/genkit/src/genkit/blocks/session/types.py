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

"""Shared session typing contracts to avoid import cycles."""

from __future__ import annotations

import asyncio
from typing import Protocol

from genkit.aio import Channel
from genkit.blocks.model import GenerateResponseChunkWrapper, GenerateResponseWrapper
from genkit.types import Message


class GenkitLike(Protocol):
    """Minimal Genkit surface needed by session/chat."""

    async def generate(self, *args: object, **kwargs: object) -> GenerateResponseWrapper[object]:
        """Generate content using the Genkit instance."""
        ...

    def generate_stream(
        self, *args: object, **kwargs: object
    ) -> tuple[
        Channel[GenerateResponseChunkWrapper, GenerateResponseWrapper[object]],
        asyncio.Future[GenerateResponseWrapper[object]],
    ]:
        """Generate streaming content using the Genkit instance."""
        ...


class SessionLike(Protocol):
    """Minimal Session surface needed by Chat."""

    _ai: GenkitLike

    @property
    def id(self) -> str:
        """Return the session ID."""
        ...

    def get_messages(self, thread_name: str) -> list[Message]:
        """Return messages for the named thread."""
        ...

    def update_messages(self, thread_name: str, messages: list[Message]) -> None:
        """Replace messages for the named thread."""
        ...

    async def save(self) -> None:
        """Persist session state."""
        ...
