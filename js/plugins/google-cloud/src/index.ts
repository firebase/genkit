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
import { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { Sampler } from '@opentelemetry/sdk-trace-base';
import { GoogleAuth, JWTInput } from 'google-auth-library';
import { GcpLogger } from './gcpLogger.js';
import { GcpOpenTelemetry } from './gcpOpenTelemetry.js';

export interface PluginOptions {
  projectId?: string;
  telemetryConfig?: TelemetryConfig;
  credentials?: JWTInput;
}

export interface TelemetryConfig {
  sampler?: Sampler;
  autoInstrumentation?: boolean;
  autoInstrumentationConfig?: InstrumentationConfigMap;
  metricExportIntervalMillis?: number;
  metricExportTimeoutMillis?: number;
  instrumentations?: Instrumentation[];

  /** When true, metrics are not sent to GCP. */
  disableMetrics?: boolean;

  /** When true, traces are not sent to GCP. */
  disableTraces?: boolean;

  /** When true, telemetry data will be exported, even for local runs */
  forceDevExport?: boolean;
}

/**
 * Provides a plugin for using Genkit with GCP.
 */
export const googleCloud: Plugin<[PluginOptions] | []> = genkitPlugin(
  'googleCloud',
  async (options?: PluginOptions) => {
    let authClient;
    let credentials;

    // Allow customers to pass in cloud credentials from environment variables
    // following: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
    if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
      const serviceAccountCreds = JSON.parse(
        process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
      );
      const authOptions = { credentials: serviceAccountCreds };
      authClient = new GoogleAuth(authOptions);

      credentials = await authClient.getCredentials();
    } else {
      authClient = new GoogleAuth();
    }

    const projectId = options?.projectId || (await authClient.getProjectId());

    const optionsWithProjectIdAndCreds = {
      ...options,
      projectId,
      credentials,
    };

    return {
      telemetry: {
        instrumentation: {
          id: 'googleCloud',
          value: new GcpOpenTelemetry(optionsWithProjectIdAndCreds),
        },
        logger: {
          id: 'googleCloud',
          value: new GcpLogger(optionsWithProjectIdAndCreds),
        },
      },
    };
  }
);

export default googleCloud;
export * from './gcpLogger.js';
export * from './gcpOpenTelemetry.js';
