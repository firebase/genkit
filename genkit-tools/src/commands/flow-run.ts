import { Command } from 'commander';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';
import { startRunner } from '../utils/runner-utils';
import { Runner } from '../runner/runner';
import { logger } from '../utils/logger';

interface FlowRunOptions {
  wait?: boolean;
}

/** Command to start GenKit server, optionally without static file serving */
export const flowRun = new Command('flow:run')
  .argument('<flowName>', 'name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .action(async (flowName: string, data: string, options: FlowRunOptions) => {
    const runner = await startRunner();

    logger.info(`Running '/flow/${flowName}'...`);
    const startState = (await runner.runAction({
      key: `/flow/${flowName}`,
      input: {
        start: {
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
          input: data ? JSON.parse(data) : undefined,
        },
      } as FlowInvokeEnvelopeMessage,
    })) as FlowState;

    if (!startState.operation.done && options.wait) {
      logger.info('Started flow run, waiting for it to complete...');
      const finalState = await waitForFlowToComplete(
        runner,
        flowName,
        startState.flowId
      );
      logger.info(
        'Flow completed:\n' +
          JSON.stringify(finalState.operation, undefined, '  ')
      );
    } else {
      logger.info(
        'Flow operation:\n' +
          JSON.stringify(startState.operation, undefined, '  ')
      );
    }

    await runner.stop();
  });

async function waitForFlowToComplete(
  runner: Runner,
  flowName: string,
  flowId: string
): Promise<FlowState> {
  let state;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    state = await getFlowState(runner, flowName, flowId);
    if (state.operation.done) {
      break;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return state;
}

async function getFlowState(
  runner: Runner,
  flowName: string,
  flowId: string
): Promise<FlowState> {
  return (await runner.runAction({
    key: `/flow/${flowName}`,
    input: {
      state: {
        flowId,
      },
    } as FlowInvokeEnvelopeMessage,
  })) as FlowState;
}
