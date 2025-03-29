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

"""Google AI sample."""

import asyncio

import structlog

from genkit.ai import Genkit
from genkit.plugins.google_ai import (
    GoogleAi,
    GoogleAiPluginOptions,
    googleai_name,
)
from genkit.plugins.google_ai.models import gemini
from genkit.types import GenerationCommonConfig, Message, Role, TextPart

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAi(plugin_params=GoogleAiPluginOptions())],
    model=googleai_name(gemini.GoogleAiVersion.GEMINI_2_0_FLASH),
)


@ai.flow()
async def say_hi(data: str):
    """Generate a greeting.

    Args:
        data: The data to generate a greeting for.

    Returns:
        The generated greeting.
    """
    return await ai.generate(messages=[Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])])


async def say_hi_with_configured_temperature(data: str):
    """Generate a greeting with a configured temperature.

    Args:
        data: The data to generate a greeting for.

    Returns:
        The generated greeting.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])],
        config=GenerationCommonConfig(temperature=0.1),
    )


async def main() -> None:
    """Main entry point for the Google AI sample.

    This function demonstrates how to use the Google AI plugin to generate text
    using the Gemini 2.0 Flash model.
    """
    await logger.ainfo(await say_hi(', tell me a joke'))
    await logger.ainfo(await say_hi_with_configured_temperature(', tell me a joke'))


if __name__ == '__main__':
    asyncio.run(main())
