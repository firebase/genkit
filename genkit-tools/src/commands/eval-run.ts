import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { readFile, writeFile } from 'fs/promises';

interface EvalRunOptions {
  output?: string;
}
/** Command to run evaluation on a dataset. */
export const evalRun = new Command('eval:run')
  .argument(
    '<dataset>',
    'Dataset to evaluate on (currently only supports JSON)'
  )
  .option(
    '--output <filename>',
    'name of the output file to write evaluation results'
  )
  .action(async (dataset: string, options: EvalRunOptions) => {
    const runner = await startRunner();

    logger.debug(`Loading data from '${dataset}'...`);
    const loadedData = JSON.parse((await readFile(dataset)).toString('utf-8'));

    const evaluatorActions = Object.keys(await runner.listActions()).filter(
      (name) => name.startsWith('/evaluator')
    );
    if (!evaluatorActions) {
      logger.error('No evaluators installed');
      return undefined;
    }
    const results: Record<string, any> = {};
    await Promise.all(
      evaluatorActions.map(async (e) => {
        logger.info(`Running evaluator '${e}'...`);
        const response = await runner.runAction({
          key: e,
          input: {
            dataset: loadedData,
          },
        });
        results[e] = response;
      })
    );

    if (options.output) {
      logger.info(`Writing results to '${options.output}'...`);
      await writeFile(options.output, JSON.stringify(results, undefined, '  '));
    } else {
      console.log(JSON.stringify(results, undefined, '  '));
    }

    await runner.stop();
  });
