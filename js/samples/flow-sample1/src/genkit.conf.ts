import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { firebase } from '@google-genkit/plugin-firebase';

export default configureGenkit({
  plugins: [firebase({ projectId: getProjectId() })],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
