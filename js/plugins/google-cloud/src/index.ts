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
import { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { Sampler } from '@opentelemetry/sdk-trace-base';
import { GoogleAuth } from 'google-auth-library';
import { FirestoreTraceStore } from './firestoreTraceStore.js';
import { GcpLogger } from './gcpLogger.js';
import { GcpOpenTelemetry } from './gcpOpenTelemetry.js';

export { defineFirestoreRetriever } from './firestoreRetriever.js';
export { FirestoreTraceStore } from './firestoreTraceStore.js';
export * from './gcpLogger.js';
export * from './gcpOpenTelemetry.js';

/**
 * Parameters for the Google Cloud plugin.
 */
export interface GoogleCloudPluginParams {
  /** GCP project ID to use. If not provided, the default project ID is used. */
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
  /** Configuration for the OpenTelemetry telemetry exporter. */
  telemetryConfig?: TelemetryConfig;
}

/**
 * Configuration for the OpenTelemetry telemetry exporter.
 */
export interface TelemetryConfig {
  /** Sampler to use for tracing. */
  sampler?: Sampler;
  /** Whether to automatically instrument the application. */
  autoInstrumentation?: boolean;
  /** Configuration for auto-instrumentation. */
  autoInstrumentationConfig?: InstrumentationConfigMap;
  /** Interval in milliseconds at which to export metrics. */
  metricExportIntervalMillis?: number;
  /** Timeout in milliseconds for metric export. */
  metricExportTimeoutMillis?: number;
  /** Instrumentations to use. */
  instrumentations?: Instrumentation[];
  /** When true, metrics are not sent to GCP. */
  disableMetrics?: boolean;
  /** When true, traces are not sent to GCP. */
  disableTraces?: boolean;
  /** When true, telemetry data will be exported, even for local runs. */
  forceDevExport?: boolean;
}

/**
 * Provides a Google Cloud plugin for Genkit.
 */
export const googleCloud: Plugin<[GoogleCloudPluginParams] | []> = genkitPlugin(
  'googleCloud',
  async (params?: GoogleCloudPluginParams) => {
    const authClient = new GoogleAuth();
    const projectId = params?.projectId || (await authClient.getProjectId());
    const paramsWithProjectId = {
      ...params,
      projectId,
    };

    return {
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
          id: 'googleCloud',
          value: new GcpOpenTelemetry(paramsWithProjectId),
        },
        logger: {
          id: 'googleCloud',
          value: new GcpLogger(paramsWithProjectId),
        },
      },
    };
  }
);

export default googleCloud;
