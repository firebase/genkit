import { Runner } from '../runner/runner';

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
