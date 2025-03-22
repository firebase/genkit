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

import asyncio

from genkit.ai import Genkit
from genkit.core.typing import GenerationCommonConfig, Message, Role, TextPart
from genkit.plugins.google_ai import (
    GoogleAi,
    GoogleAiPluginOptions,
    googleai_name,
)
from genkit.plugins.google_ai.models import gemini

ai = Genkit(
    plugins=[GoogleAi(plugin_params=GoogleAiPluginOptions())],
    model=googleai_name(gemini.GoogleAiVersion.GEMINI_2_0_FLASH),
)


@ai.flow()
async def say_hi(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ]
    )


async def say_hi_with_configured_temperature(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ],
        config=GenerationCommonConfig(temperature=0.1),
    )


def main() -> None:
    print(asyncio.run(say_hi(', tell me a joke')).message.content)
    print(
        asyncio.run(
            say_hi_with_configured_temperature(', tell me a joke')
        ).message.content
    )


if __name__ == '__main__':
    main()
