// Example.

import { Command } from 'commander';
import { logger } from '../utils/logger';

interface ExampleOptions {
  uppercase?: boolean;
}

/** Example command. Registered in cli.ts */
export const example = new Command('example')
  .option('-u, --uppercase', 'Uppercase the output', false)
  .action((options: ExampleOptions) => {
    const message = 'this is an example command';
    if (options.uppercase) {
      logger.warn(message.toUpperCase());
    } else {
      logger.info(message);
    }
  });
