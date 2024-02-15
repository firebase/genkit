import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { firestoreStores } from '@google-genkit/providers/stores';

export default configureGenkit({
  plugins: [firestoreStores({ projectId: getProjectId() })],
  flowStateStore: 'firestoreStores',
  traceStore: 'firestoreStores',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
