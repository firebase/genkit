import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [firebase({ projectId: getProjectId() }), googleAI(), openAI()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
