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
  ProcessManager,
  RuntimeEvent,
  RuntimeManager,
  type GenkitToolsError,
} from '@genkit-ai/tools-common/manager';
import { logger } from '@genkit-ai/tools-common/utils';
import * as crypto from 'crypto';
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

export interface DevProcessManagerOptions {
  disableRealtimeTelemetry?: boolean;
  nonInteractive?: boolean;
}

export async function startDevProcessManager(
  projectRoot: string,
  command: string,
  args: string[],
  options?: DevProcessManagerOptions
): Promise<{ manager: RuntimeManager; processPromise: Promise<void> }> {
  const telemetryServerUrl = await resolveTelemetryServer(projectRoot);
  const disableRealtimeTelemetry = options?.disableRealtimeTelemetry ?? false;
  const runtimeId = crypto.randomUUID().substring(0, 8);
  const envVars: Record<string, string> = {
    GENKIT_TELEMETRY_SERVER: telemetryServerUrl,
    GENKIT_ENV: 'dev',
    GENKIT_RUNTIME_ID: runtimeId,
  };
  if (!disableRealtimeTelemetry) {
    envVars.GENKIT_ENABLE_REALTIME_TELEMETRY = 'true';
  }
  const processManager = new ProcessManager(command, args, envVars);
  const manager = await RuntimeManager.create({
    telemetryServerUrl,
    manageHealth: true,
    projectRoot,
    processManager,
    disableRealtimeTelemetry,
  });
  const processPromise = processManager.start({ ...options, cwd: projectRoot });

  await waitForRuntime(manager, runtimeId, processPromise);

  return { manager, processPromise };
}

/**
 * Waits for the runtime with the given ID to register itself.
 * Rejects if the process exits or if the timeout is reached.
 */
export async function waitForRuntime(
  manager: RuntimeManager,
  runtimeId: string,
  processPromise: Promise<void>
): Promise<void> {
  if (manager.getRuntimeById(runtimeId)) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    let timeoutId: NodeJS.Timeout;
    let unsubscribe: () => void;

    const cleanup = () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (unsubscribe) unsubscribe();
    };

    timeoutId = setTimeout(() => {
      cleanup();
      reject(new Error('Timeout waiting for runtime to be ready'));
    }, 30000);

    unsubscribe = manager.onRuntimeEvent((event, runtime) => {
      if (event === RuntimeEvent.ADD && runtime.id === runtimeId) {
        cleanup();
        resolve();
      }
    });

    processPromise
      .then(() => {
        cleanup();
        reject(new Error('Process exited before runtime was ready'));
      })
      .catch((err) => {
        cleanup();
        reject(err);
      });
  });
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
