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
import {
  GcpLogger,
  GcpOpenTelemetry,
  TelemetryConfig,
} from '@genkit-ai/google-cloud';
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
  async (params?: FirestorePluginParams) => ({
    flowStateStore: {
      id: 'firestore',
      value: new FirestoreStateStore(params?.flowStateStore),
    },
    traceStore: {
      id: 'firestore',
      value: new FirestoreTraceStore(params?.traceStore),
    },
    telemetry: {
      instrumentation: {
        id: 'firebase',
        value: new GcpOpenTelemetry(params),
      },
      logger: {
        id: 'firebase',
        value: new GcpLogger(params),
      },
    },
  })
);
