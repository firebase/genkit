import { Plugin } from '@google-genkit/common/config';
import { FirestoreTraceStore } from '@google-genkit/common/tracing';
import { FirestoreStateStore } from '@google-genkit/flow';

export function firestoreStores(params?: {
  collection?: string;
  databaseId?: string;
  projectId?: string;
}): Plugin {
  return {
    name: 'firestoreStores',
    provides: {
      flowStateStore: {
        id: 'firestore',
        value: new FirestoreStateStore(params),
      },
      traceStore: {
        id: 'firestore',
        value: new FirestoreTraceStore(params),
      },
    },
  };
}
