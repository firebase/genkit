/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { getLocation, getProjectId } from '@genkit-ai/core';
import { configureGenkit } from '@genkit-ai/core/config';
import { firebase } from '@genkit-ai/firebase';
import { gpt4Turbo, openAI } from '@genkit-ai/openai';
import { RagasMetric, ragas } from '@genkit-ai/ragas';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/vertex-ai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
    ragas({
      judge: gpt4Turbo,
      metrics: [
        RagasMetric.FAITHFULNESS,
        RagasMetric.ANSWER_RELEVANCY,
        RagasMetric.CONTEXT_UTILIZATION,
      ],
      embedder: textEmbeddingGecko,
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
