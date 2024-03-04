import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { readFile } from 'fs/promises';

/** Command to run evaluation on a dataset. */
export const evalRun = new Command('eval:run')
  .argument(
    '<dataset>',
    'Dataset to evaluate on (currently only supports JSON)'
  )
  .action(async (dataset: string) => {
    const runner = await startRunner();

    logger.debug(`Loading data from '${dataset}'...`);
    const loadedData = JSON.parse((await readFile(dataset)).toString('utf-8'));

    const evaluatorActions = Object.keys(await runner.listActions()).filter(
      (name) => name.startsWith('/evaluator')
    );
    if (!evaluatorActions) {
      logger.info('No evaluators installed');
      return undefined;
    }
    await Promise.all(
      evaluatorActions.map((e) => {
        logger.info(`Running evaluator '${e}'...`);
        return runner
          .runAction({
            key: e,
            input: {
              dataset: loadedData,
            },
          })
          .then((response) => {
            const results = JSON.stringify(response);
            console.log(results);
          });
      })
    );

    await runner.stop();
  });
