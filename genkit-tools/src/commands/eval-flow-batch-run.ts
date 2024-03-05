import { Command } from 'commander';

interface EvalFlowBatchRunOptions {
  output?: string;
}
/** Command to run a flow wit batch input and evaluate the output */
export const evalRun = new Command('eval:flowBatchRun')
  .argument('<flowName>', 'Name of the flow to run')
  .argument('<inputFileName>', 'JSON batch data to use to run the flow')
  .option(
    '--output <filename>',
    'Name of the output file to write evaluation results'
  )
  .action(
    async (
      flowName: string,
      fileName: string,
      options: EvalFlowBatchRunOptions
    ) => {}
  );
