import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/providers/firebase';
import { googleVertexAI } from '@google-genkit/providers/google-vertexai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleAI(),
    googleVertexAI(),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
