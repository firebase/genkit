import { genkitPlugin } from '@google-genkit/common/config';
import { FirestoreTraceStore } from '@google-genkit/common/tracing';
import { FirestoreStateStore } from '@google-genkit/flow';

interface FirestorePluginParams {
  projectId?: string;
  flowStateStore?: {
    collection?: string;
    databaseId?: string;
  };
  traceStore?: {
    collection?: string;
    databaseId?: string;
  };
}

export const firebase = genkitPlugin(
  'firebase',
  (params?: FirestorePluginParams) => ({
    flowStateStore: {
      id: 'firestore',
      value: new FirestoreStateStore(params?.flowStateStore),
    },
    traceStore: {
      id: 'firestore',
      value: new FirestoreTraceStore(params?.traceStore),
    },
  })
);
