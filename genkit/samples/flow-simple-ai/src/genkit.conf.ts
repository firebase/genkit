import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/providers/openai';
import { googleAI } from '@google-genkit/providers/google-ai';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleAI(),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
