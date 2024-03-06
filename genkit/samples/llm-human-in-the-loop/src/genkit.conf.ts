import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleGenAI } from '@google-genkit/plugin-google-genai';
import { firebase } from '@google-genkit/plugin-firebase';

export default configureGenkit({
  plugins: [firebase({ projectId: getProjectId() }), googleGenAI(), openAI()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
