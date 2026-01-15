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

import asyncio

import pytest

from genkit.ai import Genkit, Plugin
from genkit.core.action import Action, ActionMetadata
from genkit.core.registry import ActionKind
from genkit.types import GenerateRequest, GenerateResponse, Message, Role, TextPart


class AsyncResolveOnlyPlugin(Plugin):
    name = 'async-resolve-only'

    async def init(self):
        # Intentionally register nothing eagerly.
        return []

    async def resolve(self, action_type: ActionKind, name: str):
        if action_type != ActionKind.MODEL:
            return None
        if name != f'{self.name}/lazy-model':
            return None

        # Simulate async derived-options / auth fetch work.
        await asyncio.sleep(0)

        async def _generate(req: GenerateRequest, ctx):
            return GenerateResponse(
                message=Message(role=Role.MODEL, content=[TextPart(text='OK: lazy')]),
                finish_reason='stop',
            )

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=_generate,
        )

    async def list_actions(self):
        return [
            ActionMetadata(
                kind=ActionKind.MODEL,
                name=f'{self.name}/lazy-model',
            )
        ]


class AsyncInitPlugin(Plugin):
    name = 'async-init-plugin'

    async def init(self):
        async def _generate(req: GenerateRequest, ctx):
            return GenerateResponse(
                message=Message(role=Role.MODEL, content=[TextPart(text='OK: init')]),
                finish_reason='stop',
            )

        # Simulate async setup work.
        await asyncio.sleep(0)
        return [
            Action(
                kind=ActionKind.MODEL,
                name=f'{self.name}/init-model',
                fn=_generate,
            )
        ]

    async def resolve(self, action_type: ActionKind, name: str):
        return None

    async def list_actions(self):
        return [
            ActionMetadata(
                kind=ActionKind.MODEL,
                name=f'{self.name}/init-model',
            )
        ]


@pytest.mark.asyncio
async def test_async_resolve_is_awaited_via_generate():
    ai = Genkit(plugins=[AsyncResolveOnlyPlugin()])
    resp = await ai.generate('async-resolve-only/lazy-model', prompt='hello')
    assert resp.text == 'OK: lazy'


@pytest.mark.asyncio
async def test_async_init_is_awaited_via_generate():
    ai = Genkit(plugins=[AsyncInitPlugin()])
    resp = await ai.generate('async-init-plugin/init-model', prompt='hello')
    assert resp.text == 'OK: init'
