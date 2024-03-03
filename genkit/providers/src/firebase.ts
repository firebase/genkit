import { genkitPlugin, Plugin } from '@google-genkit/common/config';
import { FirestoreStateStore } from '@google-genkit/flow';
import { FirestoreTraceStore } from '../../common/lib/tracing.js';

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

export const firebase: Plugin<[FirestorePluginParams]> = genkitPlugin(
  'firebase',
  async (params?: FirestorePluginParams) => ({
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
