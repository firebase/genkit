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

import {
  LocalFileTraceStore,
  startTelemetryServer,
} from '@genkit-ai/telemetry-server';
import type { Status } from '@genkit-ai/tools-common';
import {
  RuntimeManager,
  type GenkitToolsError,
} from '@genkit-ai/tools-common/manager';
import { logger } from '@genkit-ai/tools-common/utils';
import getPort, { makeRange } from 'get-port';

/**
 * Returns the telemetry server address either based on environment setup or starts one.
 *
 * This function is not idempotent. Typically you want to make sure it's called only once per cli instance.
 */
export async function resolveTelemetryServer(
  projectRoot: string
): Promise<string> {
  let telemetryServerUrl = process.env.GENKIT_TELEMETRY_SERVER;
  if (!telemetryServerUrl) {
    const telemetryPort = await getPort({ port: makeRange(4033, 4999) });
    telemetryServerUrl = `http://localhost:${telemetryPort}`;
    await startTelemetryServer({
      port: telemetryPort,
      traceStore: new LocalFileTraceStore({
        storeRoot: projectRoot,
        indexRoot: projectRoot,
      }),
    });
  }
  return telemetryServerUrl;
}

/**
 * Starts the runtime manager and its dependencies.
 */
export async function startManager(
  projectRoot: string,
  manageHealth?: boolean
): Promise<RuntimeManager> {
  const telemetryServerUrl = await resolveTelemetryServer(projectRoot);
  const manager = RuntimeManager.create({
    telemetryServerUrl,
    manageHealth,
    projectRoot,
  });
  return manager;
}

/**
 * Runs the given function with a runtime manager.
 */
export async function runWithManager(
  projectRoot: string,
  fn: (manager: RuntimeManager) => Promise<void>
) {
  let manager: RuntimeManager;
  try {
    manager = await startManager(projectRoot, false); // Don't manage health in this case.
  } catch (e) {
    process.exit(1);
  }
  try {
    await fn(manager);
  } catch (err) {
    logger.error('Command exited with an Error:');
    const error = err as GenkitToolsError;
    if (typeof error.data === 'object') {
      const errorStatus = error.data as Status;
      const { code, details, message } = errorStatus;
      logger.error(`\tCode: ${code}`);
      logger.error(`\tMessage: ${message}`);
      logger.error(
        `\tTrace: http://localhost:4200/traces/${details.traceId}\n`
      );
    } else {
      logger.error(`\tMessage: ${error.data}\n`);
    }
    logger.error('Stack trace:');
    logger.error(`${error.stack}`);
  }
}
