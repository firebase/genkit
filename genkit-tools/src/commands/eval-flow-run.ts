import { Command } from 'commander';
import { logger } from '../utils/logger';
import { startRunner, waitForFlowToComplete } from '../utils/runner-utils';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';

// TODO: Support specifying waiting or streaming
interface EvalFlowRunOptions {
  output?: string;
}
/** Command to run a flow and evaluate the output */
export const evalRun = new Command('eval:flowRun')
  .argument('<flowName>', 'Name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option(
    '--output <filename>',
    'Name of the output file to write evaluation results'
  )
  .action(
    async (flowName: string, data: string, options: EvalFlowRunOptions) => {}
  );
