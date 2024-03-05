import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    openAI(),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
