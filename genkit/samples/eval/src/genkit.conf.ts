import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { vertexAI, geminiPro } from '@google-genkit/plugin-vertex-ai';
import { ragas, RagasMetric } from '@google-genkit/plugin-ragas';
import { firebase } from '@google-genkit/providers/firebase';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@google-genkit/providers/google-vertexai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
    googleVertexAI(),
    ragas({
      judge: geminiPro,
      metrics: [RagasMetric.ANSWER_RELEVANCY],
      embedder: textEmbeddingGecko001,
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
