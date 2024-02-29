import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleGenAI } from '@google-genkit/plugin-google-genai';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
