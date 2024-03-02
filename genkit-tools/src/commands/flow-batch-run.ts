import { Command } from 'commander';
import { FlowInvokeEnvelopeMessage, FlowState, Operation } from '../types/flow';
import { startRunner, waitForFlowToComplete } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { writeFile, readFile } from 'fs/promises';

interface FlowBatchRunOptions {
  wait?: boolean;
  output?: string;
}

/** Command to run flows with batch input. */
export const flowBatchRun = new Command('flow:batchRun')
  .argument('<flowName>', 'name of the flow to run')
  .argument('<inputFileName>', 'JSON batch data to use to run the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .option('--output <filename>', 'name of the output file to store the output')
  .action(
    async (
      flowName: string,
      fileName: string,
      options: FlowBatchRunOptions
    ) => {
      const runner = await startRunner();

      const inputData = JSON.parse(await readFile(fileName, 'utf8')) as any[];
      if (!Array.isArray(inputData)) {
        throw new Error('batch input data must be an array');
      }

      const outputValues = [] as { input: any; output: Operation }[];
      for (const data of inputData) {
        logger.info(`Running '/flow/${flowName}'...`);
        var state = (await runner.runAction({
          key: `/flow/${flowName}`,
          input: {
            start: {
              input: data,
            },
          } as FlowInvokeEnvelopeMessage,
        })) as FlowState;

        if (!state.operation.done && options.wait) {
          logger.info('Started flow run, waiting for it to complete...');
          state = await waitForFlowToComplete(runner, flowName, state.flowId);
        }
        logger.info(
          'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
        );
        outputValues.push({
          input: data,
          output: state.operation,
        });
      }

      if (options.output) {
        await writeFile(
          options.output,
          JSON.stringify(outputValues, undefined, ' ')
        );
      }

      await runner.stop();
    }
  );
