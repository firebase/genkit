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
import { Action } from '../types/action';
import { logger } from './logger';

export const EVALUATOR_ACTION_PREFIX = '/evaluator';

// Update js/ai/src/evaluators.ts if you change this value
export const EVALUATOR_METADATA_KEY_USES_LLM = 'evaluatorUsesLlm';

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
  const usesLlm = evaluatorActions.some(
    (action) =>
      action.metadata && action.metadata[EVALUATOR_METADATA_KEY_USES_LLM]
  );

  if (!usesLlm) {
    return true;
  }

  if (force) {
    logger.warn(
      'The evaluation may result in multiple calls to LLMs per example.'
    );
    return true;
  }

  const answers = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirm',
      message:
        'The evaluation may result in multiple calls to LLMs per example. Do you wish to proceed?',
      default: false,
    },
  ]);

  return answers.confirm;
}
