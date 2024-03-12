import { getProjectId, getLocation } from '@genkit-ai/common';
import { configureGenkit } from '@genkit-ai/common/config';
import { vertexAI, textembeddingGecko } from '@genkit-ai/plugin-vertex-ai';
import { openAI, gpt4Turbo } from '@genkit-ai/plugin-openai';
import { ragas, RagasMetric } from '@genkit-ai/plugin-ragas';
import { firebase } from '@genkit-ai/plugin-firebase';

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
