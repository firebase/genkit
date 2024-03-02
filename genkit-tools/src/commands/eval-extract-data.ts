import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';

interface EvalDatasetOptions {
  env: 'dev' | 'prod';
}

/** Command to extract evaluation data. */
export const evalExtractData = new Command('eval:extractData')
  .argument('<flowName>', 'name of the flow to run')
  .option('--env <env>', 'environment (dev/prod)', 'dev')
  .action(async (flowName: string, options: EvalDatasetOptions) => {
    const runner = await startRunner();

    logger.info(`Extracting trace data '/flow/${flowName}'...`);
    const traces = await runner.listTraces({
      env: options.env,
    });

    var dataset = traces.map((t) => {
      const rootSpan = Object.values(t.spans).find(
        (s) =>
          s.attributes['genkit:type'] === 'flow' &&
          s.attributes['genkit:metadata:flow:name'] === flowName &&
          s.attributes['genkit:metadata:flow:state'] === 'done'
      );
      if (!rootSpan) {
        return undefined;
      }
      // TODO: add context extraction
      return {
        input: rootSpan?.attributes['genkit:input'],
        output: rootSpan?.attributes['genkit:output'],
      };
    });
    dataset = dataset.filter((d) => !!d);

    logger.info(JSON.stringify(dataset, undefined, '  '));

    await runner.stop();
  });
