import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { writeFile } from 'fs/promises';

interface EvalDatasetOptions {
  env: 'dev' | 'prod';
  output: string;
  maxRows: string;
}

/** Command to extract evaluation data. */
export const evalExtractData = new Command('eval:extractData')
  .argument('<flowName>', 'name of the flow to run')
  .option('--env <env>', 'environment (dev/prod)', 'dev')
  .option(
    '--output <filename>',
    'name of the output file to store the extracted data',
    'out.json'
  )
  .option('--maxRows <env>', 'maximum number of rows', '100')
  .action(async (flowName: string, options: EvalDatasetOptions) => {
    const runner = await startRunner();

    logger.info(`Extracting trace data '/flow/${flowName}'...`);
    const response = await runner.listTraces({
      env: options.env,
      // TODO: this is wrong, max rows should be for the final dataset, not in the initial read.
      limit: parseInt(options.maxRows),
    });
    const traces = response.traces;

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
      const context = Object.values(t.spans)
        .filter((s) => s.attributes['genkit:metadata:subtype'] === 'retriever')
        .flatMap((s) =>
          JSON.parse(s.attributes['genkit:output'] as string).map(
            (d: { content: string }) => d.content
          )
        );
      return {
        input: rootSpan?.attributes['genkit:input'],
        output: rootSpan?.attributes['genkit:output'],
        context,
      };
    });
    dataset = dataset.filter((d) => !!d);

    logger.info(JSON.stringify(dataset, undefined, '  '));
    logger.info(`Writing data to '${options.output}'...`);
    await writeFile(options.output, JSON.stringify(dataset, undefined, '  '));

    await runner.stop();
  });
