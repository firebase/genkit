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

import { ChildProcess, execSync, spawn } from 'child_process';
import * as chokidar from 'chokidar';
import * as clc from 'colorette';
import * as fs from 'fs';
import * as path from 'path';
import { logger } from '../utils/logger';
import { getNodeEntryPoint } from '../utils/utils';
import { Action } from '../types/action';
import axios, { AxiosError } from 'axios';
import * as apis from '../types/apis';
import { TraceData } from '../types/trace';
import { GenkitToolsError, StreamingCallback } from './types';
import { FlowState } from '../types/flow';

/**
 * Files in these directories will be excluded from being watched for changes.
 */
const EXCLUDED_WATCHER_DIRS = ['node_modules'];

/**
 * Delay after detecting changes in files before triggering app reload.
 */
const RELOAD_DELAY_MS = 500;

const REFLECTION_PORT = process.env.GENKIT_REFLECTION_PORT || 3100;
const REFLECTION_API_URL = `http://localhost:${REFLECTION_PORT}/api`;

const STREAM_DELIMITER = '\n';

/**
 * Runner is responsible for watching, building, and running app code and exposing an API to control actions on that app code.
 */
export class Runner {
  /**
   * Directory that contains the app code.
   */
  readonly directory: string;

  /**
   * Whether to watch for changes and automatically rebuild/reload the app code.
   */
  readonly autoReload: boolean;

  /**
   * Subprocess for the app code. May not be running.
   */
  private appProcess: ChildProcess | null = null;

  /**
   * Watches and triggers reloads on code changes.
   */
  private watcher: chokidar.FSWatcher | null = null;

  /**
   * Delay before triggering on code changes.
   */
  private changeTimeout: NodeJS.Timeout | null = null;

  /**
   * Creates a Runner instance.
   *
   * @param options - Options for configuring the Runner:
   *   - `directory` - Directory that contains the app code (defaults to the current working directory).
   *   - `autoReload` - Whether to watch for changes and automatically rebuild/reload the app code (defaults to true).
   */
  constructor(
    options: {
      directory?: string;
      autoReload?: boolean;
    } = {}
  ) {
    this.directory = options.directory || process.cwd();
    this.autoReload = options.autoReload ?? true;
  }

  /**
   * Starts the runner.
   */
  public start(): void {
    this.startApp();
    if (this.autoReload) {
      this.watchForChanges();
    }
  }

  /**
   * Stops the runner.
   */
  public async stop(): Promise<void> {
    if (this.autoReload) {
      await this.watcher?.close();
    }
    await this.stopApp();
  }

  /**
   * Reloads the app code. If it's not running, it will be started.
   */
  public async reloadApp(): Promise<void> {
    console.info('Reloading app code...');
    if (this.appProcess) {
      await this.stopApp();
    }
    this.startApp();
  }

  /**
   * Starts the app code in a subprocess.
   * @param entryPoint - entry point of the app (e.g. index.js)
   */
  private startApp(): void {
    const entryPoint = getNodeEntryPoint(process.cwd());

    if (!fs.existsSync(entryPoint)) {
      logger.error(`Could not find \`${entryPoint}\`. App not started.`);
      return;
    }

    logger.info(`Starting app at ${entryPoint}...`);

    this.appProcess = spawn('node', [entryPoint], {
      env: {
        ...process.env,
        GENKIT_ENV: 'dev',
        GENKIT_REFLECTION_PORT: process.env.GENKIT_REFLECTION_PORT || '3100',
      },
    });

    this.appProcess.stdout?.on('data', (data) => {
      logger.info(data);
    });

    this.appProcess.stderr?.on('data', (data) => {
      logger.error(data);
    });

    this.appProcess.on('error', (error): void => {
      logger.error(`Error in app process: ${error.message}`);
    });

    this.appProcess.on('exit', (code) => {
      logger.info(`App process exited with code ${code}`);
      this.appProcess = null;
    });
  }

  /**
   * Stops the app code process.
   */
  private stopApp(): Promise<void> {
    return new Promise((resolve) => {
      if (this.appProcess && !this.appProcess.killed) {
        this.appProcess.on('exit', () => {
          this.appProcess = null;
          resolve();
        });
        this.appProcess.kill();
      } else {
        resolve();
      }
    });
  }

  /**
   * Starts watching the app directory for code changes.
   */
  private watchForChanges(): void {
    this.watcher = chokidar
      .watch(this.directory, {
        persistent: true,
        ignoreInitial: true,
        ignored: (filePath: string) => {
          return EXCLUDED_WATCHER_DIRS.some((dir) =>
            filePath.includes(path.normalize(dir))
          );
        },
      })
      .on('add', this.handleFileChange.bind(this))
      .on('change', this.handleFileChange.bind(this));
  }

  /**
   * Handles file changes in the watched directory.
   * @param filePath - path of the changed file
   */
  private handleFileChange(filePath: string): void {
    const extension = path.extname(filePath);
    const relativeFilePath = path.relative(this.directory, filePath);
    if (extension === '.ts') {
      logger.info(
        `Detected a change in ${clc.bold(relativeFilePath)}. Compiling...`
      );
      try {
        execSync('npm run build', { stdio: 'inherit' });
      } catch (error) {
        logger.error('Compilation error:', error);
      }
    } else if (extension === '.js') {
      logger.info(
        `Detected a change in ${clc.bold(
          relativeFilePath
        )}. Waiting for other changes before reloading.`
      );
      if (this.changeTimeout) {
        clearTimeout(this.changeTimeout);
      }
      this.changeTimeout = setTimeout(() => {
        void this.reloadApp();
        this.changeTimeout = null;
      }, RELOAD_DELAY_MS);
    }
  }

  private httpErrorHandler(error: AxiosError, message?: string): any {
    const newError = new GenkitToolsError(message || 'Internal Error');

    if (error.response) {
      if ((error.response?.data as any).message) {
        newError.message = (error.response?.data as any).message;
      }
      // we got a non-200 response; copy the payload and rethrow
      newError.data = error.response.data;
      throw newError;
    }

    // We actually have an exception; wrap it and re-throw.
    throw new GenkitToolsError(message || 'Internal Error', {
      cause: error.cause,
    });
  }

  /** Retrieves all runnable actions. */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${REFLECTION_API_URL}/__health`);
      if (response.status !== 200) {
        return false;
      }
      return true;
    } catch (error) {
      if ((error as AxiosError).code === 'ECONNREFUSED') {
        return false;
      }
      throw new Error('Code failed to load, please check log messages above.');
    }
  }

  async waitUntilHealthy(): Promise<void> {
    for (let i = 0; i < 200; i++) {
      const healthy = await this.healthCheck();
      if (healthy) {
        return;
      }
      await new Promise((r) => setTimeout(r, 300));
    }
    throw new Error('Timed out while waiting for code to load.');
  }

  /** Retrieves all runnable actions. */
  async listActions(): Promise<Record<string, Action>> {
    const response = await axios
      .get(`${REFLECTION_API_URL}/actions`)
      .catch((err) => this.httpErrorHandler(err, 'Error listing actions.'));

    return response.data as Record<string, Action>;
  }

  /** Runs an action. */
  async runAction(
    input: apis.RunActionRequest,
    streamingCallback?: StreamingCallback<any>
  ): Promise<unknown> {
    if (streamingCallback) {
      const response = await axios
        .post(`${REFLECTION_API_URL}/runAction?stream=true`, input, {
          headers: {
            'Content-Type': 'application/json',
          },
          responseType: 'stream',
        })
        .catch(this.httpErrorHandler);
      const stream = response.data;

      var buffer = '';
      stream.on('data', (data: string) => {
        buffer += data;
        while (buffer.includes(STREAM_DELIMITER)) {
          streamingCallback(
            JSON.parse(buffer.substring(0, buffer.indexOf(STREAM_DELIMITER)))
          );
          buffer = buffer.substring(
            buffer.indexOf(STREAM_DELIMITER) + STREAM_DELIMITER.length
          );
        }
      });
      var resolver: (op: unknown) => void;
      const promise = new Promise((r) => {
        resolver = r;
      });
      stream.on('end', () => {
        resolver(JSON.parse(buffer));
      });
      return promise;
    } else {
      const response = await axios
        .post(`${REFLECTION_API_URL}/runAction`, input, {
          headers: {
            'Content-Type': 'application/json',
          },
        })
        .catch((err) =>
          this.httpErrorHandler(err, `Error running action key='${input.key}'.`)
        );
      return response.data as unknown;
    }
  }

  /** Retrieves all traces for a given environment (e.g. dev or prod). */
  async listTraces(
    input: apis.ListTracesRequest
  ): Promise<apis.ListTracesResponse> {
    const { env, limit, continuationToken } = input;
    var query = '';
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
      .get(`${REFLECTION_API_URL}/envs/${env}/traces?${query}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error listing traces for env='${env}', query='${query}'.`
        )
      );

    return apis.ListTracesResponseSchema.parse(response.data);
  }

  /** Retrieves a trace for a given ID. */
  async getTrace(input: apis.GetTraceRequest): Promise<TraceData> {
    const { env, traceId } = input;
    const response = await axios
      .get(`${REFLECTION_API_URL}/envs/${env}/traces/${traceId}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error getting trace for traceId='${traceId}', env='${env}'.`
        )
      );

    return response.data as TraceData;
  }

  /** Retrieves all flow states for a given environment (e.g. dev or prod). */
  async listFlowStates(
    input: apis.ListFlowStatesRequest
  ): Promise<apis.ListFlowStatesResponse> {
    const { env, limit, continuationToken } = input;
    var query = '';
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
      .get(`${REFLECTION_API_URL}/envs/${env}/flowStates?${query}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error listing flowStates for env='${env}', query='${query}'.`
        )
      );

    return apis.ListFlowStatesResponseSchema.parse(response.data);
  }

  /** Retrieves a flow state for a given ID. */
  async getFlowState(input: apis.GetFlowStateRequest): Promise<FlowState> {
    const { env, flowId } = input;
    const response = await axios
      .get(`${REFLECTION_API_URL}/envs/${env}/flowStates/${flowId}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error getting flowState for flowId='${flowId}', env='${env}'.`
        )
      );

    return response.data as FlowState;
  }
}
