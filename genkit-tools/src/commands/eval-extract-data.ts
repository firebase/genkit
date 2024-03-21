/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Command } from 'commander';
import { randomUUID } from 'crypto';
import { writeFile } from 'fs/promises';
import { EvalInput } from '../eval';
import { logger } from '../utils/logger';
import { startRunner } from '../utils/runner-utils';

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
  .option('--maxRows <maxRows>', 'maximum number of rows', '100')
  .option('--label [label]', 'label flow run in this batch')
  .action(async (flowName: string, options: EvalDatasetOptions) => {
    const runner = await startRunner();
    logger.info(`Extracting trace data '/flow/${flowName}'...`);

    var dataset: EvalInput[] = [];
    var continuationToken = undefined;
    while (dataset.length < parseInt(options.maxRows)) {
      const response = await runner.listTraces({
        env: options.env,
        limit: parseInt(options.maxRows),
        continuationToken,
      });
      continuationToken = response.continuationToken;
      const traces = response.traces;
      // TODO: This assumes that all the data is in one trace, but it could be across multiple.
      // We should support this use case similar to how we do in eval-flow-run.ts
      var batch: EvalInput[] = traces
        .map((t) => {
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
          const context: string[] = Object.values(t.spans)
            .filter(
              (s) => s.attributes['genkit:metadata:subtype'] === 'retriever'
            )
            .flatMap((s) =>
              JSON.parse(s.attributes['genkit:output'] as string).map(
                (d: { content: string }) => d.content
              )
            );
          return {
            testCaseId: randomUUID(),
            input: rootSpan?.attributes['genkit:input'],
            output: rootSpan?.attributes['genkit:output'],
            context,
            // The trace (t) does not contain the traceId, so we have to pull it out of the
            // spans, de- dupe, and turn it back into an array.
            traceIds: Array.from(
              new Set(Object.values(t.spans).map((span) => span.traceId))
            ),
          } as EvalInput;
        })
        .filter((result): result is EvalInput => !!result);
      batch.forEach((d) => dataset.push(d));
      if (dataset.length > parseInt(options.maxRows)) {
        dataset = dataset.splice(0, parseInt(options.maxRows));
        break;
      }
      if (!continuationToken) {
        break;
      }
    }

    if (options.output) {
      logger.info(`Writing data to '${options.output}'...`);
      await writeFile(options.output, JSON.stringify(dataset, undefined, '  '));
    } else {
      logger.info(`Results will not be written to file.`);
      console.log(`Results: ${JSON.stringify(dataset, undefined, '  ')}`);
    }

    await runner.stop();
  });
