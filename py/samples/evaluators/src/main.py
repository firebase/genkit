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

"""Minimal evaluators sample: regex (no LLM) + LLM-as-judge."""

import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from genkit import Genkit
from genkit.evaluator import BaseDataPoint, Details, EvalFnResponse, Score
from genkit.plugins.google_genai import GoogleAI

# Setup
prompts_path = Path(__file__).resolve().parent.parent / 'prompts'
ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-2.5-flash', prompt_dir=prompts_path)

# 1. Regex evaluator (no LLM, no API key)
URL_REGEX = re.compile(r'https?://\S+')


async def url_match(datapoint: BaseDataPoint, _options: dict | None = None) -> EvalFnResponse:
    """Score: true if output contains a URL."""
    if not datapoint.output or not isinstance(datapoint.output, str):
        raise ValueError('String output required')
    found = bool(URL_REGEX.search(datapoint.output))
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=found, details=Details(reasoning=f'URL found: {found}')),
    )


ai.define_evaluator(
    name='byo/url',
    display_name='URL Match',
    definition='True if output contains a URL.',
    is_billed=False,
    fn=url_match,
)


# 2. LLM-as-judge evaluator (requires GEMINI_API_KEY)
class DeliciousnessResponse(BaseModel):
    reason: str
    verdict: Literal['yes', 'no', 'maybe']


async def deliciousness(datapoint: BaseDataPoint, _options: dict | None = None) -> EvalFnResponse:
    """Score: is the output delicious (literally or metaphorically)?"""
    if not datapoint.output:
        raise ValueError('Output required')
    prompt = ai.prompt('deliciousness')
    rendered = await prompt.render(input={'output': str(datapoint.output)})
    response = await ai.generate(
        model=os.getenv('JUDGE_MODEL', 'googleai/gemini-2.5-flash'),
        messages=rendered.messages,
        output_schema=DeliciousnessResponse,
    )
    if not response.output:
        raise ValueError(f'Parse failed: {response.text}')
    parsed = DeliciousnessResponse.model_validate(response.output)
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=parsed.verdict, details=Details(reasoning=parsed.reason)),
    )


ai.define_evaluator(
    name='byo/deliciousness',
    display_name='Deliciousness',
    definition='Is the output delicious?',
    fn=deliciousness,
)


async def main() -> None:
    pass


if __name__ == '__main__':
    ai.run_main(main())
