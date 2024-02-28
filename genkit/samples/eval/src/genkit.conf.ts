import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { vertexAI, geminiPro } from '@google-genkit/plugin-vertex-ai';
import { ragas, RagasMetric } from '@google-genkit/plugin-ragas';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
    ragas({ judge: geminiPro, metrics: [RagasMetric.CONTEXT_PRECISION] }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
