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
 * Provides a {NodeSDKConfiguration} configuration for use with the
 * Open-Telemetry SDK. This configuration allows plugins to specify how and
 * where open telemetry data will be exported.
 */
export interface TelemetryConfig {
  getConfig(): Partial<NodeSDKConfiguration>;
}

/**
 * Provides a Winston {LoggerOptions} configuration for building a Winston
 * logger. This logger will be used to write genkit debug logs.
 */
export interface LoggerConfig {
  /** Gets the logger used for writing generic log statements */
  getLogger(env: string): any;
}

/**
 * Options for configuring the Open-Telemetry export configuration as part of a
 * Genkit config file.
 */
export interface TelemetryOptions {
  /**
   * Specifies which telemetry export provider to use. The value specified here
   * must match the id of a {TelemetryConfig} provided by an installed plugin.
   *
   * Note: Telemetry data is only exported when running in the `prod`
   * environment.
   * */
  instrumentation: string;

  /**
   * Specifies which winston logging provider to use. The value specified here
   * must match the id of a {TelemetryConfig} provided by an installed plugin.
   */
  logger: string;
}
