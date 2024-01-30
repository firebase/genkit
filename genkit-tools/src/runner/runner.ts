import * as express from 'express';
import { ErrorRequestHandler } from 'express';
import * as trpcExpress from '@trpc/server/adapters/express';
import { RUNNER_ROUTER } from './router';
import { logger } from '../utils/logger';
import { exec, ChildProcess, ExecOptions } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Runner is responsible for exposing a control API, watching/building app code, starting it up, and calling it.
 */
export class Runner {
  // Running app process.
  private appProcess: ChildProcess | null = null;

  // TODO: Add constructor that allows specifying working directory and API port.

  /**
   * Starts the runner.
   */
  public start(): void {
    const entryPoint = this.getMainEntryPoint();
    this.startApp(entryPoint);
    this.watchForChanges();
    this.startApi();
  }

  /**
   * Reloads the app code. If it's not running, it will be started.
   */
  public reloadApp(): void {
    console.debug('Reloading app code...');
    this.appProcess?.on('exit', () => {
      const entryPoint = this.getMainEntryPoint();
      this.startApp(entryPoint);
    });
    this.stopApp();
  }

  /**
   * Starts a Runner API which watches changes in and controls the calling of source code.
   *
   * @param port port on which to listen
   */
  private startApi(port?: number | string | undefined): void {
    if (!port) {
      port = process.env.RUNNER_PORT || 3000;
    }
    const api = express();
    api.use(express.json());
    const errorHandler: ErrorRequestHandler = (error, request, response, next) => {
      logger.error(error.stack);
      response.status(500).send(error);
    };
    api.use(errorHandler);
    api.use(
      '/api',
      trpcExpress.createExpressMiddleware({
        router: RUNNER_ROUTER,
      }),
    );
    api.listen(port, () => {
      console.log(`Runner API running on http://localhost:${port}/api`);
    });
  }

  private startApp(entryPoint: string): void {
    logger.info(`Starting ${entryPoint}...`);
    const command = `node ${entryPoint}`;
    const options: ExecOptions = {
      env: {
        ...process.env,
        START_REFLECTION_API: 'true',
        REFLECTION_PORT: process.env.REFLECTION_PORT || '3100',
      },
    };

    this.appProcess = exec(command, options, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error.message}`);
        return;
      }
      if (stderr) {
        console.error(`Stderr: ${stderr}`);
        return;
      }
      console.log(`Stdout: ${stdout}`);
    });

    this.appProcess.stdout?.on('data', (data) => {
      console.log(data);
    });

    this.appProcess.stdout?.on('error', (error) => {
      console.log(error);
    });

    this.appProcess.on('exit', (code) => {
      console.log(`App process exited with code ${code}`);
      this.appProcess = null;
    });
  }

  private stopApp(): void {
    if (this.appProcess && !this.appProcess.killed) {
      this.appProcess.kill();
    }
  }

  private watchForChanges(): void {
    fs.watch(process.cwd(), { recursive: true }, (eventType, filename) => {
      if (
        eventType === 'change' &&
        filename &&
        path.extname(filename) === '.js'
      ) {
        const fullPath = path.join(process.cwd(), filename);
        // Check if the file exists to avoid reloading on missing code (e.g. while `tsc` is building).
        fs.stat(fullPath, (error, stats) => {
          if (!error && stats.isFile()) {
            console.log(`Detected a change in ${filename}.`);
            this.reloadApp();
          }
        });
      }
    });
  }

  private getMainEntryPoint(): string {
    const packageJsonPath = path.join(process.cwd(), 'package.json');
    if (fs.existsSync(packageJsonPath)) {
      const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      return (packageJson.main as string) || 'index.js';
    }
    return 'index.js';
  }
}
