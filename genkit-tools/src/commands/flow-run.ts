import { Command } from 'commander';
import { writeFile } from 'fs/promises';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';
import { logger } from '../utils/logger';
import { startRunner, waitForFlowToComplete } from '../utils/runner-utils';

interface FlowRunOptions {
  wait?: boolean;
  output?: string;
  stream?: boolean;
}

/** Command to start GenKit server, optionally without static file serving */
export const flowRun = new Command('flow:run')
  .argument('<flowName>', 'name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .option('-s, --stream', 'Stream output', false)
  .option(
    '--output <filename>',
    'name of the output file to store the extracted data'
  )
  .action(async (flowName: string, data: string, options: FlowRunOptions) => {
    const runner = await startRunner();

    logger.info(`Running '/flow/${flowName}' (stream=${options.stream})...`);
    var state = (await runner.runAction(
      {
        key: `/flow/${flowName}`,
        input: {
          start: {
            // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
            input: data ? JSON.parse(data) : undefined,
          },
        } as FlowInvokeEnvelopeMessage,
      },
      options.stream
        ? (chunk) => console.log(JSON.stringify(chunk, undefined, '  '))
        : undefined
    )) as FlowState;

    if (!state.operation.done && options.wait) {
      logger.info('Started flow run, waiting for it to complete...');
      state = await waitForFlowToComplete(runner, flowName, state.flowId);
    }
    logger.info(
      'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
    );
    if (options.output && state.operation.result?.response) {
      await writeFile(
        options.output,
        JSON.stringify(state.operation.result?.response, undefined, ' ')
      );
    }

    await runner.stop();
  });
