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
import os
import re
from collections.abc import Callable
from typing import Any

import jsonata

from genkit.ai import Plugin
from genkit.core.action import Action, ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema
from genkit.core.typing import EvalRequest, EvalResponse
from genkit.plugins.evaluators.constant import (
    AnswerRelevancyResponseSchema,
    GenkitMetricType,
    LongFormResponseSchema,
    MaliciousnessResponseSchema,
    MetricConfig,
    NliResponse,
    PluginOptions,
)
from genkit.plugins.metrics.helper import load_prompt_file, render_text
from genkit.types import BaseEvalDataPoint, EvalFnResponse, EvalStatusEnum, Score


def _get_prompt_path(filename: str) -> str:
    """Get absolute path to a prompt file in the prompts directory."""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(plugin_dir, '..', '..', '..', '..', 'prompts', filename)


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

    def __init__(self, params: PluginOptions | list[MetricConfig]):
        """Initialize Genkit Evaluators plugin."""
        if isinstance(params, list):
            params = PluginOptions(root=params)
        self.params = params

    async def init(self) -> list[Action]:
        return [self._create_evaluator_action(param) for param in self.params.root]

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if action_type != ActionKind.EVALUATOR:
            return None
        for param in self.params.root:
            metric_name, _, _ = self._metric_descriptor(param)
            if name == metric_name:
                return self._create_evaluator_action(param)
        return None

    async def list_actions(self) -> list[ActionMetadata]:
        metas: list[ActionMetadata] = []
        for param in self.params.root:
            metric_name, display_name, definition = self._metric_descriptor(param)
            metas.append(
                ActionMetadata(
                    kind=ActionKind.EVALUATOR,
                    name=metric_name,
                    input_json_schema=to_json_schema(EvalRequest),
                    output_json_schema=to_json_schema(EvalResponse),
                    metadata={
                        'evaluator': {
                            'label': metric_name,
                            'displayName': display_name,
                            'definition': definition,
                            'isBilled': bool(param.judge),
                        }
                    },
                )
            )
        return metas

    def _metric_descriptor(self, param: MetricConfig) -> tuple[str, str, str]:
        metric_type = param.metric_type
        match metric_type:
            case GenkitMetricType.ANSWER_RELEVANCY:
                return (
                    str(metric_type).lower(),
                    'Answer Relevancy',
                    'Assesses how pertinent the generated answer is to the given prompt',
                )
            case GenkitMetricType.FAITHFULNESS:
                return (
                    str(metric_type).lower(),
                    'Faithfulness',
                    'Measures the factual consistency of the generated answer against the given context',
                )
            case GenkitMetricType.MALICIOUSNESS:
                return (
                    str(metric_type).lower(),
                    'Maliciousness',
                    'Measures whether the generated output intends to deceive, harm, or exploit',
                )
            case GenkitMetricType.REGEX:
                return (
                    str(metric_type).lower(),
                    'RegExp',
                    'Tests output against the regexp provided as reference',
                )
            case GenkitMetricType.DEEP_EQUAL:
                return (
                    str(metric_type).lower(),
                    'Deep Equals',
                    'Tests equality of output against the provided reference',
                )
            case GenkitMetricType.JSONATA:
                return (
                    str(metric_type).lower(),
                    'JSONata',
                    'Tests JSONata expression (provided in reference) against output',
                )
            case _:
                raise ValueError(f'Unsupported metric type: {metric_type}')

    def _create_evaluator_action(self, param: MetricConfig) -> Action:
        metric_name, display_name, definition = self._metric_descriptor(param)
        metadata = {
            'evaluator': {
                'label': metric_name,
                'displayName': display_name,
                'definition': definition,
                'isBilled': bool(param.judge),
            }
        }

        metric_type = param.metric_type

        # Cache for prompts (loaded on first use) - scoped per-action to avoid cross-test coupling.
        _faithfulness_prompts: dict[str, Any] = {}

        async def eval_one(datapoint: BaseEvalDataPoint, options: Any | None, ai) -> EvalFnResponse:
            match metric_type:
                case GenkitMetricType.ANSWER_RELEVANCY:
                    assert datapoint.output is not None, 'output is required'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    prompt_function = await load_prompt_file(_get_prompt_path('faithfulness_long_form.prompt'))
                    context = ' '.join(json.dumps(e) for e in (datapoint.context or []))
                    prompt = await render_text(
                        prompt_function, {'input': input_string, 'output': output_string, 'context': context}
                    )

                    response = await ai.generate(
                        model=param.judge.name,
                        prompt=prompt,
                        config=param.judge_config,
                        output_schema=AnswerRelevancyResponseSchema,
                    )

                    out = response.output
                    answered = out.get('answered') if isinstance(out, dict) else (out.answered if out else False)
                    score = bool(answered)
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                case GenkitMetricType.FAITHFULNESS:
                    assert datapoint.output is not None, 'output is required'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    context_list = [(json.dumps(e) if not isinstance(e, str) else e) for e in (datapoint.context or [])]

                    if 'longform' not in _faithfulness_prompts:
                        _faithfulness_prompts['longform'] = await load_prompt_file(
                            _get_prompt_path('faithfulness_long_form.prompt')
                        )
                    if 'nli' not in _faithfulness_prompts:
                        _faithfulness_prompts['nli'] = await load_prompt_file(
                            _get_prompt_path('faithfulness_nli.prompt')
                        )

                    prompt = await render_text(
                        _faithfulness_prompts['longform'], {'question': input_string, 'answer': output_string}
                    )
                    longform_response = await ai.generate(
                        model=param.judge.name,
                        prompt=prompt,
                        config=param.judge_config,
                        output_schema=LongFormResponseSchema,
                    )
                    statements = (
                        longform_response.output.get('statements', [])
                        if isinstance(longform_response.output, dict)
                        else (longform_response.output.statements if longform_response.output else [])
                    )
                    if not statements:
                        raise ValueError('No statements returned')

                    all_statements = '\n'.join([f'statement: {s}' for s in statements])
                    all_context = '\n'.join(context_list)
                    prompt = await render_text(
                        _faithfulness_prompts['nli'], {'context': all_context, 'statements': all_statements}
                    )

                    nli_response = await ai.generate(
                        model=param.judge.name,
                        prompt=prompt,
                        config=param.judge_config,
                        output_schema=NliResponse,
                    )

                    nli_output = nli_response.output
                    responses = (
                        nli_output.get('responses', [])
                        if isinstance(nli_output, dict)
                        else (nli_output.responses if nli_output else [])
                    )
                    if not responses:
                        raise ValueError('Evaluator response empty')

                    faithful_count = sum(
                        1 for r in responses if (r.get('verdict') if isinstance(r, dict) else r.verdict)
                    )
                    score_val = faithful_count / len(responses)
                    reasoning = '; '.join([r.get('reason', '') if isinstance(r, dict) else r.reason for r in responses])
                    status = EvalStatusEnum.PASS_ if score_val > 0.5 else EvalStatusEnum.FAIL
                    return fill_scores(
                        datapoint,
                        Score(score=score_val, status=status, details={'reasoning': reasoning}),
                        param.status_override_fn,
                    )

                case GenkitMetricType.MALICIOUSNESS:
                    assert datapoint.output is not None, 'output is required'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    input_string = datapoint.input if isinstance(datapoint.input, str) else json.dumps(datapoint.input)
                    prompt_function = await load_prompt_file(_get_prompt_path('maliciousness.prompt'))
                    context = ' '.join(json.dumps(e) for e in (datapoint.context or []))
                    prompt = await render_text(
                        prompt_function, {'input': input_string, 'output': output_string, 'context': context}
                    )

                    response = await ai.generate(
                        model=param.judge.name,
                        prompt=prompt,
                        config=param.judge_config,
                        output_schema=MaliciousnessResponseSchema,
                    )
                    out = response.output
                    verdict = out.get('verdict') if isinstance(out, dict) else (out.verdict if out else False)
                    score = bool(verdict)
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                case GenkitMetricType.REGEX:
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (regex)'
                    output_string = (
                        datapoint.output if isinstance(datapoint.output, str) else json.dumps(datapoint.output)
                    )
                    pattern = re.compile(datapoint.reference)
                    score = pattern.search(output_string) is not None
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                case GenkitMetricType.DEEP_EQUAL:
                    assert datapoint.reference is not None, 'reference is required'
                    assert datapoint.output is not None, 'output is required'
                    score = (
                        type(datapoint.output) is type(datapoint.reference) and datapoint.output == datapoint.reference
                    )
                    status = EvalStatusEnum.PASS_ if score else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                case GenkitMetricType.JSONATA:
                    assert datapoint.output is not None, 'output is required'
                    assert datapoint.reference is not None, 'reference is required'
                    assert isinstance(datapoint.reference, str), 'reference must be of string (jsonata)'
                    expr = jsonata.Jsonata(datapoint.reference)
                    score = expr.evaluate(datapoint.output)
                    status = EvalStatusEnum.PASS_ if bool(score) else EvalStatusEnum.FAIL
                    return fill_scores(datapoint, Score(score=score, status=status), param.status_override_fn)

                case _:
                    raise ValueError(f'Unsupported metric type: {metric_type}')

        async def eval_stepper(req: EvalRequest, ctx):
            ai = (ctx.context or {}).get('__genkit_ai__')
            if ai is None:
                raise ValueError(
                    'GenkitEvaluators requires a Genkit instance in action context. Use `await ai.evaluate(...)`.'
                )

            responses: list[EvalFnResponse] = []
            for datapoint in req.dataset:
                if datapoint.test_case_id is None:
                    # Keep behavior consistent with core evaluator runner.
                    datapoint.test_case_id = 'unknown'
                try:
                    responses.append(await eval_one(datapoint, req.options, ai))
                except Exception as e:
                    responses.append(
                        EvalFnResponse(
                            test_case_id=datapoint.test_case_id,
                            evaluation=Score(
                                error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{str(e)}',
                                status=EvalStatusEnum.FAIL,
                            ),
                        )
                    )
            return EvalResponse(root=responses)

        return Action(kind=ActionKind.EVALUATOR, name=metric_name, fn=eval_stepper, metadata=metadata)
