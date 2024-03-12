import { genkitPlugin, Plugin } from '@genkit-ai/common/config';
import { FirestoreStateStore } from '@genkit-ai/flow';
import { FirestoreTraceStore } from '@genkit-ai/common/tracing';

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
