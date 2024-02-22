import { Command } from 'commander';
import { FlowState } from '../types/flow';
import { startRunner } from '../utils/runner-utils';

/** Command to start GenKit server, optionally without static file serving */
export const flowRun = new Command('flow:run')
  .argument('<flowName>', 'name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .action(async (flowName: string, data: string) => {
    const runner = await startRunner();

    console.log(`Running '/flow/${flowName}'...`);
    const state = (await runner.runAction({
      key: `/flow/${flowName}`,
      input: {
        start: {
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
          input: data ? JSON.parse(data) : undefined,
        },
      },
    })) as FlowState;
    console.log(
      'Flow operation:\n',
      JSON.stringify(state.operation, undefined, '  ')
    );

    await runner.stop();
  });
