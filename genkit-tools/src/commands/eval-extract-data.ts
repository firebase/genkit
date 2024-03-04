import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { writeFile } from 'fs/promises';

interface EvalDatasetOptions {
  env: 'dev' | 'prod';
  output?: string;
  maxRows: string;
  label?: string;
}

/** Command to extract evaluation data. */
export const evalExtractData = new Command('eval:extractData')
  .argument('<flowName>', 'name of the flow to run')
  .option('--env <env>', 'environment (dev/prod)', 'dev')
  .option(
    '--output <filename>',
    'name of the output file to store the extracted data'
  )
  .option('--maxRows <env>', 'maximum number of rows', '100')
  .option('--label [label]', 'label flow run in this batch')
  .action(async (flowName: string, options: EvalDatasetOptions) => {
    const runner = await startRunner();

    logger.info(`Extracting trace data '/flow/${flowName}'...`);

    var dataset: any[] = [];
    var continuationToken = undefined;
    while (dataset.length < parseInt(options.maxRows)) {
      const response = await runner.listTraces({
        env: options.env,
        limit: parseInt(options.maxRows),
        continuationToken,
      });
      continuationToken = response.continuationToken;
      const traces = response.traces;
      var batch = traces.map((t) => {
        const rootSpan = Object.values(t.spans).find(
          (s) =>
            s.attributes['genkit:type'] === 'flow' &&
            (!options.label ||
              s.attributes['genkit:metadata:flow:label:batchRun'] ===
                options.label) &&
            s.attributes['genkit:metadata:flow:name'] === flowName &&
            s.attributes['genkit:metadata:flow:state'] === 'done'
        );
        if (!rootSpan) {
          return undefined;
        }
        const context = Object.values(t.spans)
          .filter(
            (s) => s.attributes['genkit:metadata:subtype'] === 'retriever'
          )
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
      batch = batch.filter((d) => !!d);
      batch.forEach((d) => dataset.push(d));
      if (dataset.length > parseInt(options.maxRows)) {
        dataset = dataset.splice(0, parseInt(options.maxRows));
        break;
      }
      if (!continuationToken) {
        break;
      }
    }

    logger.info(JSON.stringify(dataset, undefined, '  '));
    if (options.output) {
      logger.info(`Writing data to '${options.output}'...`);
      await writeFile(options.output, JSON.stringify(dataset, undefined, '  '));
    }

    await runner.stop();
  });
