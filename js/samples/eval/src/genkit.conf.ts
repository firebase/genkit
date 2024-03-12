import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { vertexAI, textembeddingGecko } from '@google-genkit/plugin-vertex-ai';
import { openAI, gpt4Turbo } from '@google-genkit/plugin-openai';
import { ragas, RagasMetric } from '@google-genkit/plugin-ragas';
import { firebase } from '@google-genkit/plugin-firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
    ragas({
      judge: gpt4Turbo,
      metrics: [RagasMetric.ANSWER_RELEVANCY],
      embedder: textembeddingGecko,
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
