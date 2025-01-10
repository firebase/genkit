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

import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';

/**
 * Options governing whether Genkit will write telemetry data following the
 * OpenTelemetry Semantic Conventions for Generative AI systems:
 * https://opentelemetry.io/docs/specs/semconv/gen-ai/
 */
export interface SemConvOptions {
  writeMetrics: boolean;
  writeSpanAttributes: boolean;
  writeLogEvents: boolean;
}

/** Global options governing how Genkit will write telemetry data. */
export interface TelemetryOptions {
  semConv?: SemConvOptions;
}

/**
 * Provides a {NodeSDKConfiguration} configuration for use with the
 * Open-Telemetry SDK and other configuration options. This configuration
 * allows plugins to specify how and where open telemetry data will be
 * exported.
 */
export type TelemetryConfig = Partial<NodeSDKConfiguration> & TelemetryOptions;
