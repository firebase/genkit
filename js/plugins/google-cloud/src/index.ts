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

import { credentialsFromEnvironment } from './auth.js';
import { GcpLogger } from './gcpLogger.js';
import { GcpOpenTelemetry } from './gcpOpenTelemetry.js';
import { TelemetryConfigs } from './telemetry/defaults.js';
import { GcpPluginConfig, GcpPluginOptions } from './types.js';
import { enableTelemetry } from 'genkit/tracing';
import { logger } from 'genkit/logging';
import { getCurrentEnv } from 'genkit';

export function enableGoogleCloudTelemetry(options?: GcpPluginOptions) {
  const pluginConfig = configureGcpPlugin(options);

  enableTelemetry(new GcpOpenTelemetry(pluginConfig).getConfig())
  logger.init(new GcpLogger(pluginConfig).getLogger(getCurrentEnv()))
}

/**
 * Create a configuration object for the plugin.
 * Not normally needed, but exposed for use by the firebase plugin.
 */
async function configureGcpPlugin(
  options?: GcpPluginOptions
): Promise<GcpPluginConfig> {
  const envOptions = await credentialsFromEnvironment();
  return {
    projectId: options?.projectId || envOptions.projectId,
    credentials: options?.credentials || envOptions.credentials,
    telemetry: TelemetryConfigs.defaults(options?.telemetryConfig),
  };
}

export * from './gcpLogger.js';
export * from './gcpOpenTelemetry.js';
export { GcpPluginOptions, GcpTelemetryConfigOptions } from './types.js';
