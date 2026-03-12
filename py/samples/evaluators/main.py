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

"""Custom evaluators - regex and LLM-based. Use genkit eval:run with datasets. See README.md."""

import os
from pathlib import Path

import structlog

from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI
from src.constants import PERMISSIVE_SAFETY_SETTINGS, URL_REGEX, US_PHONE_REGEX
from src.deliciousness_evaluator import register_deliciousness_evaluator
from src.funniness_evaluator import register_funniness_evaluator
from src.pii_evaluator import register_pii_evaluator
from src.regex_evaluator import regex_matcher, register_regex_evaluators

logger = structlog.get_logger(__name__)

# Get prompts directory path
current_dir = Path(__file__).resolve().parent
prompts_path = current_dir / 'prompts'

# Register all evaluators
JUDGE_MODEL = os.getenv('JUDGE_MODEL', 'googleai/gemini-3-pro-preview')

# Initialize Genkit with Google AI plugin, default model, and load prompts
ai = Genkit(plugins=[GoogleAI()], model=JUDGE_MODEL, prompt_dir=prompts_path)

# Regex evaluators (non-LLM)
register_regex_evaluators(
    ai,
    [
        regex_matcher('url', URL_REGEX),
        regex_matcher('us_phone', US_PHONE_REGEX),
    ],
)

# LLM-based evaluators
register_pii_evaluator(ai, JUDGE_MODEL, PERMISSIVE_SAFETY_SETTINGS)
register_funniness_evaluator(ai, JUDGE_MODEL, PERMISSIVE_SAFETY_SETTINGS)
register_deliciousness_evaluator(ai, JUDGE_MODEL, PERMISSIVE_SAFETY_SETTINGS)


async def main() -> None:
    pass


if __name__ == '__main__':
    ai.run_main(main())
