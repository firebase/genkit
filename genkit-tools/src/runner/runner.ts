import * as express from 'express';
import { ErrorRequestHandler } from 'express';
import * as trpcExpress from '@trpc/server/adapters/express';
import { spawn, execSync, ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as chokidar from 'chokidar';
import * as clc from 'colorette';

import { RUNNER_ROUTER } from './router';
import { logger } from '../utils/logger';
import { getNodeEntryPoint } from '../utils/utils';

/**
 * Files in these directories will be excluded from being watched for changes.
 */
const EXCLUDED_WATCHER_DIRS = ['node_modules'];

/**
 * Delay after detecting changes in files before triggering app reload.
 */
const RELOAD_DELAY_MS = 500;

/**
 * Runner is responsible for watching, building, and running app code and exposing an API to control actions on that app code.
 */
export class Runner {
  /**
   * Directory that contains the app code.
   */
  readonly directory: string;

  /**
   * Port for the Runner API.
   */
  readonly port: number;

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
   *   * `directory` - (Optional) Directory that contains the app code (defaults to the current working directory).
   *   * `port` - (Optional) Port for the Runner API (defaults to process.env.RUNNER_PORT or 3000).
   *   * `autoReload` - (Optional) Whether to watch for changes and automatically rebuild/reload the app code (defaults to true).
   */
  constructor(
    options: {
      directory?: string;
      port?: number;
      autoReload?: boolean;
    } = {},
  ) {
    this.directory = options.directory || process.cwd();
    this.port = options.port || Number(process.env.RUNNER_PORT) || 3000;
    this.autoReload = options.autoReload || true;
  }

  /**
   * Starts the runner.
   */
  public start(): void {
    this.startApp();
    if (this.autoReload) {
      this.watchForChanges();
    }
    this.startApi();
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
   * Starts an API that controls the app code.
   */
  private startApi(): void {
    const api = express();
    api.use(express.json());
    const errorHandler: ErrorRequestHandler = (
      error,
      request,
      response,
      // Poor API doesn't allow leaving off `next` without changing the entire signature...
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      next,
    ) => {
      if (error instanceof Error) {
        logger.error(error.stack);
      }
      return response.status(500).send(error);
    };
    api.use(errorHandler);
    api.use(
      '/api',
      trpcExpress.createExpressMiddleware({
        router: RUNNER_ROUTER,
      }),
    );
    api.listen(this.port, () => {
      logger.info(`Runner API running on http://localhost:${this.port}/api`);
    });
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
        START_REFLECTION_API: 'true',
        REFLECTION_PORT: process.env.REFLECTION_PORT || '3100',
      },
    });

    this.appProcess.stdout?.on('data', (data) => {
      logger.info(data);
    });

    this.appProcess.stderr?.on('data', (data) => {
      logger.error(data);
    });

    this.appProcess.on('error', (error) => {
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
            filePath.includes(path.normalize(dir)),
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
        `Detected a change in ${clc.bold(relativeFilePath)}. Compiling...`,
      );
      try {
        execSync('tsc', { stdio: 'inherit' });
      } catch (error) {
        logger.error('Compilation error:', error);
      }
    } else if (extension === '.js') {
      logger.info(
        `Detected a change in ${clc.bold(
          relativeFilePath,
        )}. Waiting for other changes before reloading.`,
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
}
