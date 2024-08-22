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

import { EvaluatorAction } from '@genkit/ai';
import { GenerationCommonConfigSchema, ModelArgument } from '@genkit/ai/model';
import { Plugin, genkitPlugin } from '@genkit/core';
import { Criteria } from 'langchain/evaluation';
import z from 'zod';
import { langchainEvaluator } from './evaluators';

export { GenkitTracer } from './tracing.js';

interface LangchainPluginParams<
  ModelCustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
> {
  evaluators?: {
    criteria?: Criteria[];
    labeledCriteria?: Criteria[];
    judge: ModelArgument<ModelCustomOptions>;
    judgeConfig?: z.infer<ModelCustomOptions>;
  };
}

export const langchain: Plugin<[LangchainPluginParams]> = genkitPlugin(
  'langchain',
  async (params: LangchainPluginParams) => {
    const evaluators: EvaluatorAction[] = [];
    if (params.evaluators) {
      for (const criteria of params.evaluators.criteria ?? []) {
        evaluators.push(
          langchainEvaluator(
            'criteria',
            criteria,
            params.evaluators.judge,
            params.evaluators?.judgeConfig
          )
        );
      }
      for (const criteria of params.evaluators.labeledCriteria ?? []) {
        evaluators.push(
          langchainEvaluator(
            'labeled_criteria',
            criteria,
            params.evaluators.judge,
            params.evaluators?.judgeConfig
          )
        );
      }
    }
    return {
      evaluators,
    };
  }
);
