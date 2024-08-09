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

import { genkitPlugin, isDevEnv, Plugin } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { FirestoreStateStore } from '@genkit-ai/flow';
import {
  GcpLogger,
  GcpOpenTelemetry,
  TelemetryConfig,
} from '@genkit-ai/google-cloud';
import { GoogleAuth } from 'google-auth-library';
import { FirestoreTraceStore } from './firestoreTraceStore.js';
export { defineFirestoreRetriever } from './firestoreRetriever.js';

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
  telemetryConfig?: TelemetryConfig;
}

export const firebase: Plugin<[FirestorePluginParams] | []> = genkitPlugin(
  'firebase',
  async (params?: FirestorePluginParams) => {
    let projectId;
    let credentials;

    // Allow customers to pass in cloud credentials from environment variables
    // following: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
    if (process.env.GCLOUD_SERVICE_ACCOUNT) {
      const serviceAccountCreds = JSON.parse(
        process.env.GCLOUD_SERVICE_ACCOUNT
      );
      const authOptions = { credentials: serviceAccountCreds };
      const authClient = new GoogleAuth(authOptions);

      projectId = await authClient.getProjectId();
      credentials = await authClient.getCredentials();
    } else {
      const authClient = new GoogleAuth();
      projectId = params?.projectId || (await getProjectId(authClient));
    }

    const gcpOptions = {
      projectId,
      credentials,
      telemetryConfig: params?.telemetryConfig,
    };

    const flowStateStoreOptions = {
      projectId,
      credentials,
      ...params?.flowStateStore,
    };

    const traceStoreOptions = {
      projectId,
      credentials,
      ...params?.traceStore,
    };

    return {
      flowStateStore: {
        id: 'firestore',
        value: new FirestoreStateStore(flowStateStoreOptions),
      },
      traceStore: {
        id: 'firestore',
        value: new FirestoreTraceStore(traceStoreOptions),
      },
      telemetry: {
        instrumentation: {
          id: 'firebase',
          value: new GcpOpenTelemetry(gcpOptions),
        },
        logger: {
          id: 'firebase',
          value: new GcpLogger(gcpOptions),
        },
      },
    };
  }
);

async function getProjectId(authClient: GoogleAuth): Promise<string> {
  if (isDevEnv()) {
    return await authClient.getProjectId().catch((err) => {
      logger.warn(
        'WARNING: unable to determine Project ID, run "gcloud auth application-default login --project MY_PROJECT_ID"'
      );
      return '';
    });
  }

  return await authClient.getProjectId();
}
