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
import { ChildProcess, execSync, spawn } from 'child_process';
import * as chokidar from 'chokidar';
import * as clc from 'colorette';
import * as fs from 'fs';
import getPort, { makeRange } from 'get-port';
import * as path from 'path';
import terminate from 'terminate';
import { findToolsConfig } from '../plugin/config';

import {
  Action,
  RunActionResponse,
  RunActionResponseSchema,
} from '../types/action';
import * as apis from '../types/apis';
import { FlowState } from '../types/flow';
import { TraceData } from '../types/trace';
import { logger } from '../utils/logger';
import { detectRuntime, getEntryPoint } from '../utils/utils';
import { GenkitToolsError, StreamingCallback } from './types';

/**
 * Files in these directories will be excluded from being watched for changes.
 */
const EXCLUDED_WATCHER_DIRS = ['node_modules'];

/**
 * Delay after detecting changes in files before triggering app reload.
 */
const RELOAD_DELAY_MS = 500;

const STREAM_DELIMITER = '\n';

const DEFAULT_REFLECTION_PORT = 3100;

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
   * Whether to builder should be invoked when runner first starts.
   */
  readonly buildOnStart: boolean;

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

  private buildCommand?: string;

  private reflectionApiPort: number = DEFAULT_REFLECTION_PORT;
  private reflectionApiUrl = () =>
    `http://localhost:${this.reflectionApiPort}/api`;

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
      buildOnStart?: boolean;
    } = {}
  ) {
    this.directory = options.directory || process.cwd();
    this.autoReload = options.autoReload ?? true;
    this.buildOnStart = !!options.buildOnStart;
  }

  /**
   * Starts the runner.
   */
  async start(): Promise<boolean> {
    if (this.appProcess) {
      logger.info('Runner is already running.');
      return Promise.resolve(true);
    }
    if (this.autoReload || this.buildOnStart) {
      const config = await findToolsConfig();
      if (config?.runner?.mode !== 'harness') {
        this.buildCommand = config?.builder?.cmd;
        if (!this.buildCommand && detectRuntime(process.cwd()) === 'nodejs') {
          this.buildCommand = 'npm run build';
        }
        this.build();
      }
    }
    if (this.autoReload) {
      this.watchForChanges();
    }
    return this.startApp();
  }

  /**
   * Attach to an already running process at the provided address.
   */
  async attach(attachAddress: string): Promise<void> {
    this.reflectionApiPort = parseInt(new URL(attachAddress).port, 10) || 80;
    if (!(await this.healthCheck())) {
      throw new Error(
        `Unable to attach to provided external dev process address: ${attachAddress}`
      );
    }
  }

  /**
   * Stops the runner.
   */
  async stop(): Promise<void> {
    if (this.autoReload) {
      await this.watcher?.close();
    }
    await this.stopApp();
  }

  /**
   * Reloads the app code. If it's not running, it will be started.
   */
  async reloadApp(): Promise<void> {
    logger.info('Reloading app code.');
    if (this.appProcess) {
      await this.stopApp();
    }
    await this.startApp();
  }

  /**
   * Starts the app code in a subprocess.
   */
  private async startApp(): Promise<boolean> {
    const config = await findToolsConfig();
    const runtime = detectRuntime(process.cwd());
    let command = '';
    let args: string[] = [];
    switch (runtime) {
      case 'nodejs':
        if (config?.runner?.mode === 'harness') {
          const localLinkedTsPath = path.join(
            __dirname,
            '../../../node_modules/.bin/tsx'
          );
          const globallyInstalledTsxPath = path.join(
            __dirname,
            '../../../../../.bin/tsx'
          );
          if (fs.existsSync(localLinkedTsPath)) {
            command = localLinkedTsPath;
          } else if (globallyInstalledTsxPath) {
            command = globallyInstalledTsxPath;
          } else {
            throw Error(
              'Could not find tsx binary whilst running with harness.'
            );
          }
        } else {
          command = 'node';
        }
        break;
      case 'go':
        command = 'go';
        args.push('run');
        break;
      default:
        throw Error(`Unexpected runtime while starting app code: ${runtime}`);
    }

    const harnessEntryPoint = path.join(__dirname, '../runner/harness.js');
    const entryPoint =
      config?.runner?.mode === 'harness'
        ? harnessEntryPoint
        : getEntryPoint(process.cwd());
    if (!entryPoint) {
      logger.error(
        'Could not detect entry point for app. Make sure you are at the root of your project directory.'
      );
      return false;
    }
    if (!fs.existsSync(entryPoint)) {
      logger.error(`Could not find \`${entryPoint}\`. App not started.`);
      return false;
    }

    const files = config?.runner?.files;
    if (config?.runner?.mode === 'harness') {
      logger.info(
        `Running harness with file paths:\n - ${files?.join('\n - ') || ' - None'}`
      );
    } else {
      logger.info(`Starting app at \`${entryPoint}\`...`);
    }

    // Try the desired port first then fall back to default range.
    let port = await getPort({ port: this.reflectionApiPort });
    if (port !== this.reflectionApiPort) {
      port = await getPort({
        port: makeRange(DEFAULT_REFLECTION_PORT, DEFAULT_REFLECTION_PORT + 100),
      });
      logger.warn(
        `Port ${this.reflectionApiPort} not available, using ${port} instead.`
      );
    }
    this.reflectionApiPort = port;

    args.push(entryPoint);
    if (config?.runner?.mode === 'harness' && files) {
      args.push(files.join(','));
    }
    this.appProcess = spawn(command, args, {
      stdio: 'inherit',
      env: {
        ...process.env,
        GENKIT_ENV: 'dev',
        GENKIT_REFLECTION_PORT: `${this.reflectionApiPort}`,
      },
    });

    this.appProcess.on('error', (error): void => {
      logger.error(`Error in app process: ${error.message}`);
    });

    this.appProcess.on('exit', (code, signal) => {
      logger.info(`App process exited with code ${code}, signal ${signal}`);
      this.appProcess = null;
    });

    return true;
  }

  /**
   * Stops the app code process.
   */
  private async stopApp(): Promise<void> {
    return new Promise((resolve) => {
      if (this.appProcess) {
        this.appProcess.on('exit', () => {
          this.appProcess = null;
          resolve();
        });
        terminate(this.appProcess.pid!, 'SIGTERM');
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
    if (extension === '.ts' && this.buildCommand) {
      logger.info(
        `Detected a change in ${clc.bold(relativeFilePath)}. Compiling...`
      );
      try {
        this.build();
      } catch (error) {
        logger.error('Compilation error:', error);
      }
    } else if (
      extension === '.js' ||
      extension === '.ts' ||
      extension === '.prompt' ||
      extension === '.go'
    ) {
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

  private build() {
    if (this.buildCommand) {
      execSync(this.buildCommand, { stdio: 'inherit' });
    }
  }

  private httpErrorHandler(error: AxiosError, message?: string): any {
    const newError = new GenkitToolsError(message || 'Internal Error');

    if (error.response) {
      if ((error.response?.data as any).message) {
        newError.message = (error.response?.data as any).message;
      }
      // we got a non-200 response; copy the payload and rethrow
      newError.data = error.response.data as Record<string, unknown>;
      throw newError;
    }

    // We actually have an exception; wrap it and re-throw.
    throw new GenkitToolsError(message || 'Internal Error', {
      cause: error.cause,
    });
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.reflectionApiUrl()}/__health`);
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

  async sendQuit(): Promise<boolean> {
    try {
      const response = await axios.get(
        `${this.reflectionApiUrl()}/__quitquitquit`
      );
      if (response.status !== 200) {
        return false;
      }
      return true;
    } catch (error) {
      if ((error as AxiosError).code === 'ECONNREFUSED') {
        return false;
      }
      logger.debug('Failed to send quit call.');
      return false;
    }
  }

  async waitUntilHealthy(): Promise<void> {
    logger.debug(`Checking health of ${this.reflectionApiUrl()}...`);
    for (let i = 0; i < 200; i++) {
      const healthy = await this.healthCheck();
      if (healthy) {
        logger.debug('Confirmed healthy.');
        return;
      }
      await new Promise((r) => setTimeout(r, 300));
    }
    throw new Error('Timed out while waiting for code to load.');
  }

  /** Retrieves all runnable actions. */
  async listActions(): Promise<Record<string, Action>> {
    const response = await axios
      .get(`${this.reflectionApiUrl()}/actions`)
      .catch((err) => this.httpErrorHandler(err, 'Error listing actions.'));

    return response.data as Record<string, Action>;
  }

  /** Runs an action. */
  async runAction(
    input: apis.RunActionRequest,
    streamingCallback?: StreamingCallback<any>
  ): Promise<RunActionResponse> {
    if (streamingCallback) {
      const response = await axios
        .post(`${this.reflectionApiUrl()}/runAction?stream=true`, input, {
          headers: {
            'Content-Type': 'application/json',
          },
          responseType: 'stream',
        })
        .catch(this.httpErrorHandler);
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
        resolver(RunActionResponseSchema.parse(JSON.parse(buffer)));
      });
      stream.on('error', (err: Error) => {
        rejecter(err);
      });
      return promise;
    } else {
      const response = await axios
        .post(`${this.reflectionApiUrl()}/runAction`, input, {
          headers: {
            'Content-Type': 'application/json',
          },
        })
        .catch((err) =>
          this.httpErrorHandler(err, `Error running action key='${input.key}'.`)
        );
      return RunActionResponseSchema.parse(response.data);
    }
  }

  /** Retrieves all traces for a given environment (e.g. dev or prod). */
  async listTraces(
    input: apis.ListTracesRequest
  ): Promise<apis.ListTracesResponse> {
    const { env, limit, continuationToken } = input;
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
      .get(`${this.reflectionApiUrl()}/envs/${env}/traces?${query}`)
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
      .get(`${this.reflectionApiUrl()}/envs/${env}/traces/${traceId}`)
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
      .get(`${this.reflectionApiUrl()}/envs/${env}/flowStates?${query}`)
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
      .get(`${this.reflectionApiUrl()}/envs/${env}/flowStates/${flowId}`)
      .catch((err) =>
        this.httpErrorHandler(
          err,
          `Error getting flowState for flowId='${flowId}', env='${env}'.`
        )
      );

    return response.data as FlowState;
  }
}
