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

from genkit.ai import Genkit
from genkit.blocks.model import ModelReference
from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore
from genkit.plugins.evaluators import GenkitEvaluators, GenkitMetricType, MetricConfig
from genkit.plugins.google_genai import GoogleAI

# Turn off safety checks for evaluation so that the LLM as an evaluator can
# respond appropriately to potentially harmful content without error.
PERMISSIVE_SAFETY_SETTINGS = {
    'safetySettings': [
        {
            'category': 'HARM_CATEGORY_HATE_SPEECH',
            'threshold': 'BLOCK_NONE',
        },
        {
            'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
            'threshold': 'BLOCK_NONE',
        },
        {
            'category': 'HARM_CATEGORY_HARASSMENT',
            'threshold': 'BLOCK_NONE',
        },
        {
            'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
            'threshold': 'BLOCK_NONE',
        },
    ],
}

ai = Genkit(
    plugins=[
        GoogleAI(),
        GenkitEvaluators([
            MetricConfig(
                metric_type=GenkitMetricType.MALICIOUSNESS,
                judge=ModelReference(name='googleai/gemini-3-pro-preview'),
                judge_config=PERMISSIVE_SAFETY_SETTINGS,
            ),
            MetricConfig(
                metric_type=GenkitMetricType.ANSWER_RELEVANCY,
                judge=ModelReference(name='googleai/gemini-3-pro-preview'),
                judge_config=PERMISSIVE_SAFETY_SETTINGS,
            ),
            MetricConfig(
                metric_type=GenkitMetricType.FAITHFULNESS,
                judge=ModelReference(name='googleai/gemini-3-pro-preview'),
                judge_config=PERMISSIVE_SAFETY_SETTINGS,
            ),
        ]),
        DevLocalVectorStore(
            name='pdf_qa',
            embedder='googleai/text-embedding-004',
        ),
    ]
)
