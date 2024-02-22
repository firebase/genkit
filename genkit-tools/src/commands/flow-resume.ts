import { Command } from 'commander';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';

/** Command to start GenKit server, optionally without static file serving */
export const flowResume = new Command('flow:resume')
  .argument('<flowName>', 'name of the flow to resume')
  .argument('<flowId>', 'ID of the flow to resume')
  .argument('<data>', 'JSON data to use to resume the flow')
  .action(async (flowName: string, flowId: string, data: string) => {
    const runner = await startRunner();

    logger.info(`Resuming '/flow/${flowName}'`);
    const state = (await runner.runAction({
      key: `/flow/${flowName}`,
      input: {
        resume: {
          flowId,
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
          payload: JSON.parse(data),
        },
      } as FlowInvokeEnvelopeMessage,
    })) as FlowState;

    logger.info(
      'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
    );

    await runner.stop();
  });
