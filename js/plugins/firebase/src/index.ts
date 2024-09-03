/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { genkitPlugin, Plugin } from '@genkit-ai/core';
import { FirestoreStateStore } from '@genkit-ai/flow';
import { FirestoreTraceStore } from '@genkit-ai/google-cloud';
import { GoogleAuth } from 'google-auth-library';

/**
 * Parameters for the Firebase plugin.
 */
interface FirebasePluginParams {
  /** Firebase project ID. */
  projectId?: string;
  /** Configuration for the Firestore-based flow state store. */
  flowStateStore?: {
    /** Firestore collection to use. If not provided, the default collection is used. */
    collection?: string;
    /** Firestore database ID to use. If not provided, the default database ID is used. */
    databaseId?: string;
  };
  /** Configuration for the Firestore-based trace store. */
  traceStore?: {
    /** Firestore collection to use. If not provided, the default collection is used. */
    collection?: string;
    /** Firestore database ID to use. If not provided, the default database ID is used. */
    databaseId?: string;
  };
}

/**
 * Provides a Firebase plugin for Genkit.
 */
export const firebase: Plugin<[FirebasePluginParams] | []> = genkitPlugin(
  'firebase',
  async (params?: FirebasePluginParams) => {
    const authClient = new GoogleAuth();
    const projectId = params?.projectId || (await authClient.getProjectId());

    return {
      flowStateStore: {
        id: 'firestore',
        value: new FirestoreStateStore({
          ...params?.flowStateStore,
          projectId,
        }),
      },
      traceStore: {
        id: 'firestore',
        value: new FirestoreTraceStore({ ...params?.traceStore, projectId }),
      },
    };
  }
);
