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

import * as inquirer from 'inquirer';
import {
  EvalField,
  EvaluationExtractor,
  InputStepSelector,
  OutputStepSelector,
  StepSelector,
  findToolsConfig,
  isEvalField,
} from '../plugin';
import { Action } from '../types/action';
import { DocumentData, RetrieverResponse } from '../types/retrievers';
import { SpanData, TraceData } from '../types/trace';
import { logger } from './logger';

export type EvalExtractorFn = (t: TraceData) => string;
const JSON_EMPTY_STRING = '""';

export const EVALUATOR_ACTION_PREFIX = '/evaluator';

// Update js/ai/src/evaluators.ts if you change this value
export const EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName';
export const EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition';
export const EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled';

export function evaluatorName(action: Action) {
  return `${EVALUATOR_ACTION_PREFIX}/${action.name}`;
}

export function isEvaluator(key: string) {
  return key.startsWith(EVALUATOR_ACTION_PREFIX);
}

export async function confirmLlmUse(
  evaluatorActions: Action[],
  force: boolean | undefined
): Promise<boolean> {
  const isBilled = evaluatorActions.some(
    (action) =>
      action.metadata && action.metadata[EVALUATOR_METADATA_KEY_IS_BILLED]
  );

  if (!isBilled) {
    return true;
  }

  if (force) {
    logger.warn(
      'For each example, the evaluation makes calls to APIs that may result in being charged.'
    );
    return true;
  }

  const answers = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirm',
      message:
        'For each example, the evaluation makes calls to APIs that may result in being charged. Do you wish to proceed?',
      default: false,
    },
  ]);

  return answers.confirm;
}

function getRootSpan(
  trace: TraceData,
  shouldSucceed: boolean = true
): SpanData | undefined {
  return Object.values(trace.spans).find(
    (s) =>
      s.attributes['genkit:type'] === 'flow' &&
      (shouldSucceed
        ? s.attributes['genkit:metadata:flow:state'] === 'done'
        : true)
  );
}

const DEFAULT_INPUT_EXTRACTOR: EvalExtractorFn = (trace: TraceData) => {
  const rootSpan = getRootSpan(trace, /* shouldSucceed= */ false);
  return (rootSpan?.attributes['genkit:input'] as string) || JSON_EMPTY_STRING;
};
const DEFAULT_OUTPUT_EXTRACTOR: EvalExtractorFn = (trace: TraceData) => {
  const rootSpan = getRootSpan(trace);
  return (rootSpan?.attributes['genkit:output'] as string) || JSON_EMPTY_STRING;
};
const DEFAULT_CONTEXT_EXTRACTOR: EvalExtractorFn = (trace: TraceData) => {
  return JSON.stringify(
    Object.values(trace.spans)
      .filter((s) => s.attributes['genkit:metadata:subtype'] === 'retriever')
      .flatMap((s) => {
        const output: RetrieverResponse = JSON.parse(
          s.attributes['genkit:output'] as string
        );
        if (!output) {
          return [];
        }
        return output.documents.flatMap((d: DocumentData) =>
          d.content.map((c) => c.text).filter((text): text is string => !!text)
        );
      })
  );
};

const DEFAULT_EXTRACTORS: Record<EvalField, EvalExtractorFn> = {
  input: DEFAULT_INPUT_EXTRACTOR,
  output: DEFAULT_OUTPUT_EXTRACTOR,
  context: DEFAULT_CONTEXT_EXTRACTOR,
};

function getStepAttribute(
  trace: TraceData,
  stepName: string,
  attributeName?: string
): string {
  // Default to output
  const attr = attributeName ?? 'genkit:output';
  const values = Object.values(trace.spans)
    .filter((step) => step.displayName === stepName)
    .flatMap((step) => {
      return JSON.parse(step.attributes[attr] as string);
    });
  if (values.length === 0) {
    return JSON_EMPTY_STRING;
  }
  if (values.length === 1) {
    return JSON.stringify(values[0]);
  }
  // Return array if multiple steps have the same name
  return JSON.stringify(values);
}

function getExtractorFromStepName(stepName: string): EvalExtractorFn {
  return (trace: TraceData) => {
    return getStepAttribute(trace, stepName);
  };
}

function getExtractorFromStepSelector(
  stepSelector: StepSelector
): EvalExtractorFn {
  return (trace: TraceData) => {
    let stepName: string | undefined = undefined;
    let selectedAttribute: string = 'genkit:output'; // default

    if (Object.hasOwn(stepSelector, 'inputOf')) {
      stepName = (stepSelector as InputStepSelector).inputOf;
      selectedAttribute = 'genkit:input';
    } else {
      stepName = (stepSelector as OutputStepSelector).outputOf;
      selectedAttribute = 'genkit:output';
    }
    if (!stepName) {
      return JSON_EMPTY_STRING;
    } else {
      return getStepAttribute(trace, stepName, selectedAttribute);
    }
  };
}

function getExtractorMap(extractor: EvaluationExtractor) {
  let extractorMap: Record<EvalField, EvalExtractorFn> = {} as Record<
    EvalField,
    EvalExtractorFn
  >;
  for (const [key, value] of Object.entries(extractor)) {
    if (isEvalField(key)) {
      if (typeof value === 'string') {
        extractorMap[key] = getExtractorFromStepName(value);
      } else if (typeof value === 'object') {
        extractorMap[key] = getExtractorFromStepSelector(value);
      } else if (typeof value === 'function') {
        extractorMap[key] = value;
      }
    }
  }
  return extractorMap;
}

export async function getEvalExtractors(
  flowName: string
): Promise<Record<string, EvalExtractorFn>> {
  const config = await findToolsConfig();
  logger.info(`Found tools config... ${JSON.stringify(config)}`);
  const extractors = config?.evaluators
    ?.filter((e) => e.flowName === flowName)
    .map((e) => e.extractors);
  if (!extractors) {
    return Promise.resolve(DEFAULT_EXTRACTORS);
  }
  let composedExtractors = DEFAULT_EXTRACTORS;
  for (const extractor of extractors) {
    const extractorFunction = getExtractorMap(extractor);
    composedExtractors = { ...composedExtractors, ...extractorFunction };
  }
  return Promise.resolve(composedExtractors);
}
