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
import getPort, { portNumbers } from 'get-port';
import * as path from 'path';
import terminate from 'terminate';
import { ToolsConfig, findToolsConfig } from '../plugin/config';

import {
  Action,
  RunActionResponse,
  RunActionResponseSchema,
} from '../types/action';
import * as apis from '../types/apis';
import { FlowState } from '../types/flow';
import { TraceData } from '../types/trace';
import { logger } from '../utils/logger';
import {
  detectRuntime,
  getNodeEntryPoint,
  getPackageJson,
  getTsxBinaryPath,
} from '../utils/utils';
import { GenkitToolsError, StreamingCallback } from './types';

/** A command and arguments to start an app. */
interface Runnable {
  command: string;
  args: string[];
}

/** Files in these directories will be excluded from being watched for changes. */
const EXCLUDED_WATCHER_DIRS = ['node_modules'];

/** Delay after detecting changes in files before triggering app reload. */
const RELOAD_DELAY_MS = 500;

/** Delimiter for streaming responses. */
const STREAM_DELIMITER = '\n';

/** Default port for the Reflection API. */
const DEFAULT_REFLECTION_PORT = 3100;

/**
 * Runner is responsible for watching, building, and running app code and exposing an API to control actions on that app code.
 */
export class Runner {
  /** Directory that contains the app code. */
  readonly directory: string;

  /** Whether to watch for changes and automatically rebuild/reload the app code. */
  readonly autoReload: boolean;

  /** Whether to builder should be invoked when runner first starts. */
  readonly buildOnStart: boolean;

  /** Subprocess for the app code. May not be running. */
  private appProcess: ChildProcess | null = null;

  /** Watches and triggers reloads on code changes. */
  private watcher: chokidar.FSWatcher | null = null;

  /** Delay before triggering on code changes. */
  private changeTimeout: NodeJS.Timeout | null = null;

  /** Command to build the app code. */
  private buildCommand?: string;

  /** Port for the Reflection API. */
  private reflectionApiPort: number = DEFAULT_REFLECTION_PORT;

  /** URL for the Reflection API. */
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

  /** Starts the runner (code watcher, app process, builder, etc) and waits until healthy. */
  async start(): Promise<void> {
    if (this.appProcess) {
      logger.warn('Runner is already running.');
      return;
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
    await this.startApp();
    await this.waitUntilHealthy();
  }

  /** Stops the runner. */
  async stop(): Promise<void> {
    if (this.autoReload) {
      await this.watcher?.close();
    }
    await this.stopApp();
  }

  /** Attach to an already running process at the provided address. */
  async attach(attachAddress: string): Promise<void> {
    this.reflectionApiPort = parseInt(new URL(attachAddress).port, 10) || 80;
    if (!(await this.healthCheck())) {
      throw new Error(
        `Unable to attach to provided external dev process address: ${attachAddress}`
      );
    }
  }

  /** Reloads the app code. If it's not running, it will be started. */
  async reloadApp(): Promise<void> {
    logger.info('Reloading app code...');
    if (this.appProcess) {
      await this.stopApp();
    }
    await this.startApp();
  }

  /** Starts the app code in a subprocess. */
  private async startApp(): Promise<boolean> {
    const { command, args } = await this.getRunnable();
    const port = await this.getAvailablePort();
    const appProcess = spawn(command, args, {
      stdio: 'inherit',
      env: {
        ...process.env,
        GENKIT_ENV: 'dev',
        GENKIT_REFLECTION_PORT: `${port}`,
      },
    });
    appProcess.on('error', (error): void => {
      logger.error(`Error in app process: ${error.message}`);
    });
    appProcess.on('exit', (code, signal) => {
      logger.info(`App process exited with code ${code}, signal ${signal}.`);
      this.appProcess = null;
    });
    this.appProcess = appProcess;
    return true;
  }

  /** Returns the command and arguments to start the app. */
  private async getRunnable(): Promise<Runnable> {
    const runtime = detectRuntime();
    const config = await findToolsConfig();
    switch (runtime) {
      case 'nodejs':
        return config?.runner?.mode === 'harness'
          ? this.getHarnessRunnable(config)
          : this.getNodeRunnable();
      case 'go':
        return { command: 'go', args: ['run', '.'] };
      default:
        throw new Error(
          'App not found. Please run `genkit start` from the root of your project.'
        );
    }
  }

  /** Returns the command and arguments to start a harness. */
  private getHarnessRunnable(config: ToolsConfig | null): Runnable {
    const files = config?.runner?.files || [];
    if (files.length === 0) {
      throw new Error('No files provided for harness mode.');
    }
    logger.info(`Starting harness with file paths:\n - ${files.join('\n - ')}`);
    return {
      command: getTsxBinaryPath(),
      args: [path.join(__dirname, './harness.js'), files.join(',')],
    };
  }

  /** Returns the command and arguments to start a Node.js app. */
  private getNodeRunnable(): Runnable {
    const packageJson = getPackageJson();
    const scripts = packageJson?.scripts || {};
    for (const script of ['genkit:start', 'dev', 'start']) {
      if (scripts[script]) {
        logger.info(`Starting Node app using \`${script}\` script...`);
        return { command: 'npm', args: ['run', script] };
      }
    }
    const entryPoint = getNodeEntryPoint();
    if (!fs.existsSync(entryPoint)) {
      throw new Error(`Node entry point \`${entryPoint}\` not found.`);
    }
    logger.info(`Starting Node app at entry point \`${entryPoint}\`...`);
    return { command: 'node', args: [entryPoint] };
  }

  /** Returns a port that is available for the Reflection API. */
  private async getAvailablePort(): Promise<number> {
    const port = await getPort({
      port: portNumbers(this.reflectionApiPort, this.reflectionApiPort + 10),
    });
    if (port !== this.reflectionApiPort) {
      logger.warn(
        `Port ${this.reflectionApiPort} not available, using ${port} instead.`
      );
    }
    return port;
  }

  /** Stops the app code process. */
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

  /** Starts watching the app directory for code changes. */
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

  /** Handles file changes in the watched directory. */
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
      throw new Error(
        'App code failed to load, please check log messages above.' +
          'If there are no messages, make sure that you included `configureGenkit()` in your app code.'
      );
    }
  }

  /** Waits until the runner is healthy. */
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
    throw new Error('Timed out while waiting for app code to load.');
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
