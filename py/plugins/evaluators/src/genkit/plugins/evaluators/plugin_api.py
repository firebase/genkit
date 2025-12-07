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


import json
import re
from collections.abc import Callable
from typing import Any

import jsonata
from dotpromptz.typing import DataArgument

from genkit.ai import GenkitRegistry, Plugin
from genkit.plugins.evaluators.constant import GenkitMetricType, MetricConfig, PluginOptions
from genkit.types import BaseEvalDataPoint, EvalFnResponse, EvalStatusEnum, Score
from plugins.evaluators.src.metrics.helper import load_prompt_file, render_text


def evaluators_name(name: str) -> str:
    """Create an evaluators plugin name.

    Args:
        name: Name for the evaluator.

    Returns:
        The fully qualified genkitEval action name.
    """
    return f'genkitEval/{name}'


def fill_scores(
    datapoint: BaseEvalDataPoint,
    score: Score,
    status_override_fn: Callable[[Score], EvalStatusEnum] | None = None,
) -> EvalFnResponse:
    """Adds status overrides if provided."""
    status = score.status
    if status_override_fn is not None:
        status = status_override_fn(score)
    score.status = status
    return EvalFnResponse(test_case_id=datapoint.test_case_id, evaluation=score)


class GenkitEvaluators(Plugin):
    """Genkit Evaluator plugin to assess LLM output quality."""

    name = 'genkitEval'

    def __init__(self, params: PluginOptions):
        """Initialize Genkit Evaluators plugin."""
        self.params = params

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions with the registry."""
        for param in self.params.root:
            self._configure_evaluator(ai=ai, param=param)

    def _configure_evaluator(self, ai: GenkitRegistry, param: MetricConfig):
        """Validates and configures supported evaluators."""
        metric_type = param.metric_type
        match metric_type:
            case GenkitMetricType.ANSWER_RELEVANCY:

                async def _relevancy_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (regex)'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    prompt = await load_prompt_file('../../prompts/faithfulness_long_form.prompt')
                    await render_text(prompt, {'input': input_string, 'output': output_string})

                    score = None
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.MALICIOUSNESS).lower()),
                    display_name='Answer Relevancy',
                    definition='Assesses how pertinent the generated answer is to the given prompt',
                    fn=_relevancy_eval,
                )
            case GenkitMetricType.FAITHFULNESS:

                async def _faithfulness_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (regex)'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    prompt = await load_prompt_file('../../prompts/faithfulness_long_form.prompt')
                    await render_text(prompt, {'input': input_string, 'output': output_string})

                    score = None
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.MALICIOUSNESS).lower()),
                    display_name='Faithfulness',
                    definition='Measures the factual consistency of the generated answer against the given context',
                    fn=_faithfulness_eval,
                )

            case GenkitMetricType.MALICIOUSNESS:

                async def _maliciousness_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (regex)'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    prompt = await load_prompt_file('../../prompts/maliciousness.prompt')
                    await render_text(prompt, {'input': input_string, 'output': output_string})

                    score = None
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.MALICIOUSNESS).lower()),
                    display_name='Maliciousness',
                    definition='Measures whether the generated output intends to deceive, harm, or exploit',
                    fn=_maliciousness_eval,
                )

            case GenkitMetricType.REGEX:

                async def _regex_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (regex)'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    pattern = re.compile(datapoint.reference)
                    score = False if pattern.search(output_string) is None else True
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.REGEX).lower()),
                    display_name='RegExp',
                    definition='Tests output against the regexp provided as reference',
                    fn=_regex_eval,
                )

            case GenkitMetricType.DEEP_EQUAL:

                async def _deep_equal_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.reference is not None, 'reference is required'
                    assert datapoint.output is not None, 'output is required'
                    score = False
                    if type(datapoint.output) is type(datapoint.reference):
                        if datapoint.output == datapoint.reference:
                            score = True
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.DEEP_EQUAL).lower()),
                    display_name='Deep Equals',
                    definition="""Tests equality of output against the provided reference""",
                    fn=_deep_equal_eval,
                )

            case GenkitMetricType.JSONATA:

                async def _jsonata_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (jsonata)'
                    expr = jsonata.Jsonata(datapoint.reference)
                    score = expr.evaluate(datapoint.output)
                    status = EvalStatusEnum.PASS_ if bool(score) else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.JSONATA).lower()),
                    display_name='JSONata',
                    definition="""Tests JSONata expression (provided in reference) against output""",
                    fn=_jsonata_eval,
                )
