import { Command } from 'commander';
import { Runner } from '../runner/runner';
import { FlowState } from '../types/flow';

/** Command to start GenKit server, optionally without static file serving */
export const flowRun = new Command('flow:run')
  .argument('<flowName>', 'name of the low to run')
  .argument('<data>', 'JSON data to use to start the flow')
  .action(async (flowName: string, data: string) => {
    const runner = new Runner({ autoReload: false });
    runner.start();

    console.log('Waiting for code to load...');
    let attempt = 0;
    while (!(await runner.healthCheck())) {
      console.log('sleep');
      await new Promise((r) => setTimeout(r, 500));
      attempt++;
      if (attempt >= 100) {
        break;
      }
    }
    const runnerHealthy = await runner.healthCheck();
    if (runnerHealthy) {
      console.log(`will try to run '/flow/${flowName}'`);
      const state = (await runner.runAction({
        key: `/flow/${flowName}`,
        input: {
          start: {
            // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
            input: JSON.parse(data),
          },
        },
      })) as FlowState;
      console.log('state', state.operation);
    } else {
      console.error(
        'Timed out while waiting to load the code. Please check logs for errors.',
      );
    }

    await runner.stop();
  });
