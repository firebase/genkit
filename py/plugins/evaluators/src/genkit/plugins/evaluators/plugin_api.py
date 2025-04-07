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


from typing import Any

from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness
from ragas.run_config import RunConfig

from genkit.ai import GenkitRegistry, Plugin
from genkit.plugins.evaluators.constant import GenkitMetricType, MetricConfig, PluginOptions
from genkit.plugins.evaluators.model_wrapper import GenkitModel
from genkit.types import BaseEvalDataPoint, EvalFnResponse, Score


def evaluators_name(name: str) -> str:
    """Create an evaluators plugin name.

    Args:
        name: Name for the evaluator.

    Returns:
        The fully qualified genkitEval action name.
    """
    return f'genkitEval/{name}'


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
            case GenkitMetricType.FAITHFULNESS:
                assert param.judge_model is not None, 'judge_model is required'
                model = GenkitModel(ai=ai, model=param.judge_model, config=param.judge_config)

                async def _faithfulness_eval(datapoint: BaseEvalDataPoint, options: Any | None):
                    sample = SingleTurnSample(
                        user_input=datapoint.input, response=datapoint.output, retrieved_contexts=datapoint.context
                    )
                    scorer = Faithfulness(llm=model)
                    score = await scorer.single_turn_ascore(sample)
                    return EvalFnResponse(
                        test_case_id=datapoint.test_case_id,
                        evaluation=Score(score=score),
                    )

                ai.define_evaluator(
                    name=evaluators_name(str(GenkitMetricType.FAITHFULNESS).lower()),
                    display_name='Faithfulness',
                    definition='Measures the factual consistency of the generated answer against the given context',
                    fn=_faithfulness_eval,
                )
