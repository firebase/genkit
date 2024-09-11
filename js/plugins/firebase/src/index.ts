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
  configureGcpPlugin,
  GcpLogger,
  GcpOpenTelemetry,
  GcpTelemetryConfigOptions,
} from '@genkit-ai/google-cloud';
import { JWTInput } from 'google-auth-library';
import { GcpPluginConfig } from '../../google-cloud/lib/types.js';
import { FirestoreTraceStore } from './firestoreTraceStore.js';
export { defineFirestoreRetriever } from './firestoreRetriever.js';

export interface FirestorePluginParams {
  projectId?: string;
  credentials?: JWTInput;
  flowStateStore?: {
    collection?: string;
    databaseId?: string;
  };
  traceStore?: {
    collection?: string;
    databaseId?: string;
  };
  telemetryConfig?: GcpTelemetryConfigOptions;
}

export const firebase: Plugin<[FirestorePluginParams] | []> = genkitPlugin(
  'firebase',
  async (params?: FirestorePluginParams) => {
    const gcpConfig: GcpPluginConfig = await configureGcpPlugin(params);

    if (isDevEnv() && !gcpConfig.projectId) {
      // Helpful warning, since Cloud SDKs probably will not work
      logger.warn(
        'WARNING: unable to determine Firebase Project ID. Run "gcloud auth application-default login --project MY_PROJECT_ID"'
      );
    }

    const flowStateStoreOptions = {
      projectId: gcpConfig.projectId,
      credentials: gcpConfig.credentials,
      ...params?.flowStateStore,
    };
    const traceStoreOptions = {
      projectId: gcpConfig.projectId,
      credentials: gcpConfig.credentials,
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
          value: new GcpOpenTelemetry(gcpConfig),
        },
        logger: {
          id: 'firebase',
          value: new GcpLogger(gcpConfig),
        },
      },
    };
  }
);
