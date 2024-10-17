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

import { LoggingWinston } from '@google-cloud/logging-winston';
import { logger } from 'genkit/logging';
import { Writable } from 'stream';
import { resolveCurrentPrincipal } from './auth';
import { GcpTelemetryConfig } from './types';

type GrpcError = Error & {
  code?: number;
  statusDetails?: Record<string, any>[];
};

/**
 * Additional streams for writing log data to. Useful for unit testing.
 */
let additionalStream: Writable;

/**
 * Provides a logger for exporting Genkit debug logs to GCP Cloud
 * logs.
 */
export class GcpLogger {
  constructor(private readonly config: GcpTelemetryConfig) {}

  async getLogger(env: string) {
    // Dynamically importing winston here more strictly controls
    // the import order relative to registering instrumentation
    // with OpenTelemetry. Incorrect import order will trigger
    // an internal OT warning and will result in logs not being
    // associated with correct spans/traces.
    const winston = await import('winston');
    const format = this.shouldExport(env)
      ? { format: winston.format.json() }
      : {
          format: winston.format.printf((info): string => {
            return `[${info.level}] ${info.message}`;
          }),
        };

    let transports: any[] = [];
    let instructionsLogged = false; // only log the first time
    transports.push(
      this.shouldExport(env)
        ? new LoggingWinston({
            projectId: this.config.projectId,
            labels: { module: 'genkit' },
            prefix: 'genkit',
            logName: 'genkit_log',
            credentials: this.config.credentials,
            defaultCallback: async (err) => {
              // Use the defaultLogger so that logs don't get swallowed by
              // the open telemetry exporter
              const defaultLogger = logger.defaultLogger;
              const grpcError = err as GrpcError;
              if (err && this.loggingDenied(grpcError)) {
                if (!instructionsLogged) {
                  instructionsLogged = true;
                  defaultLogger.error(
                    `Unable to send logs to Google Cloud: ${grpcError.message}\n\n${await this.loggingDeniedHelpMessage()}\n`
                  );
                }
              } else if (err) {
                defaultLogger.error(
                  `Unable to send logs to Google Cloud: ${err}`
                );
              }
            },
          })
        : new winston.transports.Console()
    );
    if (additionalStream) {
      transports.push(
        new winston.transports.Stream({ stream: additionalStream })
      );
    }
    return winston.createLogger({
      transports: transports,
      ...format,
    });
  }

  private loggingDenied(err: GrpcError) {
    return (
      err.code === 7 &&
      err.statusDetails?.some((details) => {
        return details?.metadata?.permission === 'logging.logEntries.create';
      })
    );
  }

  private async loggingDeniedHelpMessage() {
    const principal = await resolveCurrentPrincipal();
    return `Add the role 'roles/logging.logWriter' to your Service Account in the IAM & Admin page on the Google Cloud console, or use the following command:\n\ngcloud projects add-iam-policy-binding ${principal.projectId ?? '${PROJECT_ID}'} \\\n    --member=serviceAccount:${principal.serviceAccountEmail || '${SERVICE_ACCT}'} \\\n    --role=roles/logging.logWriter`;
  }

  private shouldExport(env?: string) {
    return this.config.export;
  }
}

export function __addTransportStreamForTesting(stream: Writable) {
  additionalStream = stream;
}
