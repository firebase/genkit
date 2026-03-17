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
# SPDX-License-Identifier: Apache-2.0

"""Custom evaluators sample: one regex evaluator and one LLM judge."""

import os
import re
from typing import Literal

from pydantic import BaseModel

from genkit import Genkit
from genkit._core._typing import BaseDataPoint, Details, EvalFnResponse, Score
from genkit.plugins.google_genai import GoogleAI

JUDGE = os.getenv('JUDGE_MODEL', 'googleai/gemini-2.0-flash')
ai = Genkit(plugins=[GoogleAI()], model=JUDGE) if os.getenv('GEMINI_API_KEY') else Genkit()

# --- Regex evaluator (no LLM) ---


def _regex_eval(pattern: re.Pattern[str]):
    async def fn(datapoint: BaseDataPoint, _options=None) -> EvalFnResponse:
        if not datapoint.output or not isinstance(datapoint.output, str):
            raise ValueError('String output required')
        matched = bool(pattern.search(datapoint.output))
        return EvalFnResponse(
            test_case_id=datapoint.test_case_id or '',
            evaluation=Score(
                score=matched,
                details=Details(reasoning=f'{"Matched" if matched else "No match"}: {pattern.pattern}'),
            ),
        )

    return fn


ai.define_evaluator(
    name='byo/url',
    display_name='URL Presence',
    definition='Checks whether the output contains a URL.',
    is_billed=False,
    fn=_regex_eval(re.compile(r'https?://[^\s]+')),
)

# --- LLM-as-judge evaluator ---


class DeliciousnessScore(BaseModel):
    verdict: Literal['yes', 'no', 'maybe']
    reason: str


async def _deliciousness_eval(datapoint: BaseDataPoint, _options=None) -> EvalFnResponse:
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('Set GEMINI_API_KEY to run the LLM-as-judge evaluator.')
    if not datapoint.output:
        raise ValueError('Output required')
    response = await ai.generate(
        model=JUDGE,
        prompt=f'Is the following output delicious? Answer yes/no/maybe and a reason.\n\nOutput: {datapoint.output}',
        output_schema=DeliciousnessScore,
    )
    parsed = DeliciousnessScore.model_validate(response.output)
    return EvalFnResponse(
        test_case_id=datapoint.test_case_id or '',
        evaluation=Score(score=parsed.verdict, details=Details(reasoning=parsed.reason)),
    )


ai.define_evaluator(
    name='byo/deliciousness',
    display_name='Deliciousness',
    definition='Determines if the output sounds delicious.',
    fn=_deliciousness_eval,
)


async def main() -> None:
    """Run the regex evaluator once with a demo datapoint."""

    datapoint = BaseDataPoint(
        input='Check whether the output contains a URL.',
        output='Visit https://firebase.google.com for details.',
        test_case_id='demo',
    )
    result = await _regex_eval(re.compile(r'https?://[^\s]+'))(datapoint)
    print(result.model_dump_json(indent=2))  # noqa: T201


if __name__ == '__main__':
    ai.run_main(main())
