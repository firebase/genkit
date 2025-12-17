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
from pathlib import Path

import structlog

from genkit.ai import Genkit
from genkit.blocks.prompt import load_prompt_folder
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)


# Initialize with GoogleAI plugin
ai = Genkit(plugins=[GoogleAI()])


async def main():


    # Load the prompts from the directory (data)
    current_dir = Path(__file__).resolve().parent
    prompts_path = current_dir.parent / 'data'
    load_prompt_folder(ai.registry, prompts_path)

    # List actions to verify loading
    actions = ai.registry.list_serializable_actions()

    # Filter for prompts to be specific
    # Keys start with /prompt
    prompts = [key for key in actions.keys() if key.startswith(('/prompt/', '/executable-prompt/'))]

    await logger.ainfo('Registry Status', total_actions=len(actions), loaded_prompts=prompts)

    if not prompts:
        await logger.awarning('No prompts found! Check directory structure.')


if __name__ == '__main__':
    ai.run_main(main())
