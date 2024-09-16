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
import { credentialsFromEnvironment } from './auth.js';
import { GcpLogger } from './gcpLogger.js';
import { GcpOpenTelemetry } from './gcpOpenTelemetry.js';
import { TelemetryConfigs } from './telemetry/defaults.js';
import { GcpPluginConfig, GcpPluginOptions } from './types.js';

/**
 * Provides a plugin for using Genkit with GCP.
 */
export const googleCloud: Plugin<[GcpPluginOptions] | []> = genkitPlugin(
  'googleCloud',
  async (options?: GcpPluginOptions) => build(options)
);

/**
 * Configures and builds the plugin.
 * Not normally needed, but exposed for use by the firebase plugin.
 */
export async function build(options?: GcpPluginOptions) {
  const pluginConfig = await configureGcpPlugin(options);
  return {
    telemetry: {
      instrumentation: {
        id: 'googleCloud',
        value: new GcpOpenTelemetry(pluginConfig),
      },
      logger: {
        id: 'googleCloud',
        value: new GcpLogger(pluginConfig),
      },
    },
  };
}

/**
 * Create a configuration object for the plugin.
 * Not normally needed, but exposed for use by the firebase plugin.
 */
export async function configureGcpPlugin(
  options?: GcpPluginOptions
): Promise<GcpPluginConfig> {
  const envOptions = await credentialsFromEnvironment();
  return {
    projectId: options?.projectId || envOptions.projectId,
    credentials: options?.credentials || envOptions.credentials,
    telemetry: TelemetryConfigs.defaults(options?.telemetryConfig),
  };
}

export default googleCloud;
export * from './gcpLogger.js';
export * from './gcpOpenTelemetry.js';
export { GcpPluginOptions, GcpTelemetryConfigOptions } from './types.js';
