import { Runner } from '../runner/runner';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';

/**
 * Start the runner and waits for it to fully load -- reflection API to become avaialble.
 */
export async function startRunner(): Promise<Runner> {
  const runner = new Runner({ autoReload: false });
  runner.start();

  console.log('Waiting for code to load...');
  let attempt = 0;
  while (!(await runner.healthCheck())) {
    await new Promise((r) => setTimeout(r, 500));
    attempt++;
    if (attempt >= 100) {
      break;
    }
  }
  if (!(await runner.healthCheck())) {
    await runner.stop();
    throw new Error('Failed to load the code. Check logs for error messages.');
  }
  return runner;
}

/**
 * Poll and wait for the flow to fully complete.
 */
export async function waitForFlowToComplete(
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

/**
 * Retrieve the flow state.
 */
export async function getFlowState(
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
