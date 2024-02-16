import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/providers/firebase';

export default configureGenkit({
  plugins: [firebase({ projectId: getProjectId() }), googleAI()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
