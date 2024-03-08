import { Command } from 'commander';
import { startServer } from '../server';
import { Runner } from '../runner/runner';
import { logger } from '../utils/logger';

interface StartOptions {
  headless?: boolean;
  port: string;
}

/** Command to start GenKit server, optionally without static file serving */
export const start = new Command('start')
  .option(
    '-x, --headless',
    'Do not serve static UI files (for development)',
    false
  )
  .option('-p, --port <number>', 'Port to serve on. Default is 4000', '4000')
  .action((options: StartOptions) => {
    const port = Number(options.port);
    if (isNaN(port) || port < 0) {
      logger.error(`"${options.port}" is not a valid port number`);
      return;
    }

    const runner = new Runner();
    runner.start();
    return startServer(runner, options.headless ?? false, port);
  });
