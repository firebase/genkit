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

import axios, { AxiosError } from 'axios';
import chokidar from 'chokidar';
import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import {
  Action,
  RunActionResponse,
  RunActionResponseSchema,
} from '../types/action';
import * as apis from '../types/apis';
import { GenkitError } from '../types/error';
import { TraceData } from '../types/trace';
import { logger } from '../utils/logger';
import {
  DevToolsInfo,
  checkServerHealth,
  findRuntimesDir,
  findServersDir,
  isValidDevToolsInfo,
  projectNameFromGenkitFilePath,
  removeToolsInfoFile,
  retriable,
} from '../utils/utils';
import {
  GenkitToolsError,
  RuntimeEvent,
  RuntimeInfo,
  StreamingCallback,
} from './types';

const STREAM_DELIMITER = '\n';
const HEALTH_CHECK_INTERVAL = 5000;
export const GENKIT_REFLECTION_API_SPEC_VERSION = 1;

interface RuntimeManagerOptions {
  /** URL of the telemetry server. */
  telemetryServerUrl?: string;
  /** Whether to clean up unhealthy runtimes. */
  manageHealth?: boolean;
}

export class RuntimeManager {
  private filenameToRuntimeMap: Record<string, RuntimeInfo> = {};
  private filenameToDevUiMap: Record<string, DevToolsInfo> = {};
  private idToFileMap: Record<string, string> = {};
  private eventEmitter = new EventEmitter();

  private constructor(
    readonly telemetryServerUrl?: string,
    private manageHealth: boolean = true
  ) {}

  /**
   * Creates a new runtime manager.
   */
  static async create(options: RuntimeManagerOptions) {
    const manager = new RuntimeManager(
      options.telemetryServerUrl,
      options.manageHealth ?? true
    );
    await manager.setupRuntimesWatcher();
    await manager.setupDevUiWatcher();
    if (manager.manageHealth) {
      setInterval(
        async () => await manager.performHealthChecks(),
        HEALTH_CHECK_INTERVAL
      );
    }
    return manager;
  }

  /**
   * Lists all active runtimes.
   */
  listRuntimes(): Record<string, RuntimeInfo> {
    return Object.fromEntries(
      Object.values(this.filenameToRuntimeMap).map((runtime) => [
        runtime.id,
        runtime,
      ])
    );
  }

  /**
   * Gets the runtime info for a given ID.
   */
  getRuntimeById(id: string): RuntimeInfo | undefined {
    const fileName = this.idToFileMap[id];
    return fileName ? this.filenameToRuntimeMap[fileName] : undefined;
  }

  /**
   * Gets the runtime that was started most recently.
   */
  getMostRecentRuntime(): RuntimeInfo | undefined {
    const runtimes = Object.values(this.filenameToRuntimeMap);
    return runtimes.length === 0
      ? undefined
      : runtimes.reduce((a, b) =>
          new Date(a.timestamp) > new Date(b.timestamp) ? a : b
        );
  }

  /**
   * Gets the Dev UI that was started most recently.
   */
  getMostRecentDevUI(): DevToolsInfo | undefined {
    const toolsInfo = Object.values(this.filenameToDevUiMap);
    return toolsInfo.length === 0
      ? undefined
      : toolsInfo.reduce((a, b) =>
          new Date(a.timestamp) > new Date(b.timestamp) ? a : b
        );
  }

  /**
   * Subscribe to changes to the available runtimes. e.g.) whenever a new
   * runtime is added or removed.
   *
   * The `listener` will be called with the `eventType` that occured and the
   * `runtime` to which it applies.
   *
   * @param listener the callback function.
   */
  onRuntimeEvent(
    listener: (eventType: RuntimeEvent, runtime: RuntimeInfo) => void
  ) {
    Object.values(RuntimeEvent).forEach((event) =>
      this.eventEmitter.on(event, (rt) => listener(event, rt))
    );
  }

  /**
   * Retrieves all runnable actions.
   */
  async listActions(): Promise<Record<string, Action>> {
    // TODO: Allow selecting a runtime by pid.
    const runtime = this.getMostRecentRuntime();
    if (!runtime) {
      throw new Error('No runtimes found');
    }
    const response = await axios
      .get(`${runtime.reflectionServerUrl}/api/actions`)
      .catch((err) => this.httpErrorHandler(err, 'Error listing actions.'));
    return response.data as Record<string, Action>;
  }

  /**
   * Runs an action.
   */
  async runAction(
    input: apis.RunActionRequest,
    streamingCallback?: StreamingCallback<any>
  ): Promise<RunActionResponse> {
    // TODO: Allow selecting a runtime by pid.
    const runtime = this.getMostRecentRuntime();
    if (!runtime) {
      throw new Error('No runtimes found');
    }
    if (streamingCallback) {
      const response = await axios
        .post(
          `${runtime.reflectionServerUrl}/api/runAction?stream=true`,
          input,
          {
            headers: {
              'Content-Type': 'application/json',
            },
            responseType: 'stream',
          }
        )
        .catch(this.httpErrorHandler);
      let genkitVersion: string;
      if (response.headers['x-genkit-version']) {
        genkitVersion = response.headers['x-genkit-version'];
      }
      const stream = response.data;

      let buffer = '';
      stream.on('data', (data: string) => {
        buffer += data;
        while (buffer.includes(STREAM_DELIMITER)) {
          try {
            streamingCallback(
              JSON.parse(buffer.substring(0, buffer.indexOf(STREAM_DELIMITER)))
            );
            buffer = buffer.substring(
              buffer.indexOf(STREAM_DELIMITER) + STREAM_DELIMITER.length
            );
          } catch (err) {
            logger.error(`Bad stream: ${err}`);
            break;
          }
        }
      });
      let resolver: (op: RunActionResponse) => void;
      let rejecter: (err: Error) => void;
      const promise = new Promise<RunActionResponse>((resolve, reject) => {
        resolver = resolve;
        rejecter = reject;
      });
      stream.on('end', () => {
        const parsedBuffer = JSON.parse(buffer);
        if (parsedBuffer.error) {
          const err = new GenkitToolsError(
            `Error running action key='${input.key}'.`
          );
          // massage the error into a shape dev ui expects
          err.data = {
            ...parsedBuffer.error,
            stack: (parsedBuffer.error?.details as any).stack,
            data: {
              genkitErrorMessage: parsedBuffer.error?.message,
              genkitErrorDetails: parsedBuffer.error?.details,
            },
          };
          rejecter(err);
          return;
        }
        const actionResponse = RunActionResponseSchema.parse(parsedBuffer);
        if (genkitVersion) {
          actionResponse.genkitVersion = genkitVersion;
        }
        resolver(actionResponse);
      });
      stream.on('error', (err: Error) => {
        rejecter(err);
      });
      return promise;
    } else {
      const response = await axios
        .post(`${runtime.reflectionServerUrl}/api/runAction`, input, {
          headers: {
            'Content-Type': 'application/json',
          },
        })
        .catch((err) =>
          this.httpErrorHandler(err, `Error running action key='${input.key}'.`)
        );
      const resp = RunActionResponseSchema.parse(response.data);
      if (response.headers['x-genkit-version']) {
        resp.genkitVersion = response.headers['x-genkit-version'];
      }
      return resp;
    }
  }

  /**
   * Retrieves all traces
   */
  async listTraces(
    input: apis.ListTracesRequest
  ): Promise<apis.ListTracesResponse> {
    const { limit, continuationToken } = input;
    let query = '';
    if (limit) {
      query += `limit=${limit}`;
    }
    if (continuationToken) {
      if (query !== '') {
        query += '&';
      }
      query += `continuationToken=${continuationToken}`;
    }

    const response = await axios
      .get(`${this.telemetryServerUrl}/api/traces?${query}`)
      .catch((err) =>
        this.httpErrorHandler(err, `Error listing traces for query='${query}'.`)
      );

    return apis.ListTracesResponseSchema.parse(response.data);
  }

  /**
   * Retrieves a trace for a given ID.
   */
  async getTrace(input: apis.GetTraceRequest): Promise<TraceData> {
    const { traceId } = input;
    const response = await axios
      .get(`${this.telemetryServerUrl}/api/traces/${traceId}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error getting trace for traceId='${traceId}'`
        )
      );

    return response.data as TraceData;
  }

  /**
   * Notifies the runtime of dependencies it may need (e.g. telemetry server URL).
   */
  private async notifyRuntime(runtime: RuntimeInfo) {
    try {
      await axios.post(`${runtime.reflectionServerUrl}/api/notify`, {
        telemetryServerUrl: this.telemetryServerUrl,
        reflectionApiSpecVersion: GENKIT_REFLECTION_API_SPEC_VERSION,
      });
    } catch (error) {
      logger.error(`Failed to notify runtime ${runtime.id}: ${error}`);
    }
  }

  /**
   * Sets up a watcher for the runtimes directory.
   */
  private async setupRuntimesWatcher() {
    try {
      const runtimesDir = await findRuntimesDir();
      await fs.mkdir(runtimesDir, { recursive: true });
      const watcher = chokidar.watch(runtimesDir, {
        persistent: true,
        ignoreInitial: false,
      });
      watcher.on('add', (filePath) => this.handleNewRuntime(filePath));
      if (this.manageHealth) {
        watcher.on('unlink', (filePath) => this.handleRemovedRuntime(filePath));
      }
      // eagerly check existing runtimes on first load.
      for (const runtime of await fs.readdir(runtimesDir)) {
        await this.handleNewRuntime(path.resolve(runtimesDir, runtime));
      }
    } catch (error) {
      logger.error('Failed to set up runtimes watcher:', error);
    }
  }

  /**
   * Sets up a watcher for the servers directory.
   */
  private async setupDevUiWatcher() {
    try {
      const serversDir = await findServersDir();
      await fs.mkdir(serversDir, { recursive: true });
      const watcher = chokidar.watch(serversDir, {
        persistent: true,
        ignoreInitial: false,
      });
      watcher.on('add', (filePath) => this.handleNewDevUi(filePath));
      if (this.manageHealth) {
        watcher.on('unlink', (filePath) => this.handleRemovedDevUi(filePath));
      }
      // eagerly check existing Dev UI on first load.
      for (const toolsInfo of await fs.readdir(serversDir)) {
        await this.handleNewDevUi(path.resolve(serversDir, toolsInfo));
      }
    } catch (error) {
      logger.error('Failed to set up tools server watcher:', error);
    }
  }

  /**
   * Handles a new Dev UI file.
   */
  private async handleNewDevUi(filePath: string) {
    try {
      const { content, toolsInfo } = await retriable(
        async () => {
          const content = await fs.readFile(filePath, 'utf-8');
          const toolsInfo = JSON.parse(content) as DevToolsInfo;
          return { content, toolsInfo };
        },
        { maxRetries: 10, delayMs: 500 }
      );

      if (isValidDevToolsInfo(toolsInfo)) {
        const fileName = path.basename(filePath);
        if (await checkServerHealth(toolsInfo.url)) {
          this.filenameToDevUiMap[fileName] = toolsInfo;
        } else {
          logger.debug('Found an unhealthy tools config file', fileName);
          await removeToolsInfoFile(fileName);
        }
      } else {
        logger.error(`Unexpected file in the servers directory: ${content}`);
      }
    } catch (error) {
      logger.info('Error reading tools config', error);
      return undefined;
    }
  }

  /**
   * Handles a removed Dev UI file.
   */
  private handleRemovedDevUi(filePath: string) {
    const fileName = path.basename(filePath);
    if (fileName in this.filenameToDevUiMap) {
      const toolsInfo = this.filenameToDevUiMap[fileName];
      delete this.filenameToDevUiMap[fileName];
      logger.debug(`Removed Dev UI with url ${toolsInfo.url}.`);
    }
  }

  /**
   * Handles a new runtime file.
   */
  private async handleNewRuntime(filePath: string) {
    try {
      const { content, runtimeInfo } = await retriable(
        async () => {
          const content = await fs.readFile(filePath, 'utf-8');
          const runtimeInfo = JSON.parse(content) as RuntimeInfo;
          runtimeInfo.projectName = projectNameFromGenkitFilePath(filePath);
          return { content, runtimeInfo };
        },
        { maxRetries: 10, delayMs: 500 }
      );

      if (isValidRuntimeInfo(runtimeInfo)) {
        const fileName = path.basename(filePath);
        if (await checkServerHealth(runtimeInfo.reflectionServerUrl)) {
          if (
            runtimeInfo.reflectionApiSpecVersion !=
            GENKIT_REFLECTION_API_SPEC_VERSION
          ) {
            if (
              !runtimeInfo.reflectionApiSpecVersion ||
              runtimeInfo.reflectionApiSpecVersion <
                GENKIT_REFLECTION_API_SPEC_VERSION
            ) {
              logger.warn(
                'Genkit CLI is newer than runtime library. Some feature may not be supported. ' +
                  'Consider upgrading your runtime library version (debug info: expected ' +
                  `${GENKIT_REFLECTION_API_SPEC_VERSION}, got ${runtimeInfo.reflectionApiSpecVersion}).`
              );
            } else {
              logger.error(
                'Genkit CLI version is outdated. Please update `genkit-cli` to the latest version.'
              );
              process.exit(1);
            }
          }
          this.filenameToRuntimeMap[fileName] = runtimeInfo;
          this.idToFileMap[runtimeInfo.id] = fileName;
          this.eventEmitter.emit(RuntimeEvent.ADD, runtimeInfo);
          await this.notifyRuntime(runtimeInfo);
          logger.debug(
            `Added runtime with ID ${runtimeInfo.id} at URL: ${runtimeInfo.reflectionServerUrl}`
          );
        } else {
          await this.removeRuntime(fileName);
        }
      } else {
        logger.error(`Unexpected file in the runtimes directory: ${content}`);
      }
    } catch (error) {
      logger.error(`Error processing file ${filePath}:`, error);
    }
  }

  /**
   * Handles a removed runtime file.
   */
  private handleRemovedRuntime(filePath: string) {
    const fileName = path.basename(filePath);
    if (fileName in this.filenameToRuntimeMap) {
      const runtime = this.filenameToRuntimeMap[fileName];
      delete this.filenameToRuntimeMap[fileName];
      delete this.idToFileMap[runtime.id];
      this.eventEmitter.emit(RuntimeEvent.REMOVE, runtime);
      logger.debug(`Removed runtime with id ${runtime.id}.`);
    }
  }

  /**
   * Handles an HTTP error.
   */
  private httpErrorHandler(error: AxiosError, message?: string): any {
    const newError = new GenkitToolsError(message || 'Internal Error');

    if (error.response) {
      if ((error.response?.data as any).message) {
        newError.message = (error.response?.data as any).message;
      }
      // we got a non-200 response; copy the payload and rethrow
      newError.data = error.response.data as GenkitError;
      throw newError;
    }

    // We actually have an exception; wrap it and re-throw.
    throw new GenkitToolsError(message || 'Internal Error', {
      cause: error.cause,
    });
  }

  /**
   * Performs health checks on all runtimes.
   */
  private async performHealthChecks() {
    const healthCheckPromises = Object.entries(this.filenameToRuntimeMap).map(
      async ([fileName, runtime]) => {
        if (!(await checkServerHealth(runtime.reflectionServerUrl))) {
          await this.removeRuntime(fileName);
        }
      }
    );
    return Promise.all(healthCheckPromises);
  }

  /**
   * Removes the runtime file which will trigger the removal watcher.
   */
  private async removeRuntime(fileName: string) {
    const runtime = this.filenameToRuntimeMap[fileName];
    if (runtime) {
      try {
        const runtimesDir = await findRuntimesDir();
        const runtimeFilePath = path.join(runtimesDir, fileName);
        await fs.unlink(runtimeFilePath);
      } catch (error) {
        logger.debug(`Failed to delete runtime file: ${error}`);
      }
      logger.debug(
        `Removed unhealthy runtime with ID ${runtime.id} from manager.`
      );
    }
  }
}

/**
 * Checks if the runtime file is valid.
 */
function isValidRuntimeInfo(data: any): data is RuntimeInfo {
  return (
    typeof data === 'object' &&
    typeof data.id === 'string' &&
    typeof data.pid === 'number' &&
    typeof data.reflectionServerUrl === 'string' &&
    typeof data.timestamp === 'string' &&
    !isNaN(Date.parse(data.timestamp))
  );
}
