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

import { EmbedderReference, ModelReference, z } from 'genkit';
import { StatusOverrideFn } from 'genkit/evaluator';

export enum GenkitMetric {
  FAITHFULNESS = 'FAITHFULNESS',
  ANSWER_RELEVANCY = 'ANSWER_RELEVANCY',
  MALICIOUSNESS = 'MALICIOUSNESS',
}

export interface BaseGenkitMetricConfig {
  type: GenkitMetric;
  statusOverrideFn?: StatusOverrideFn;
}

export interface FaithfulnessGenkitMetricConfig<
  ModelCustomOptions extends z.ZodTypeAny,
> extends BaseGenkitMetricConfig {
  type: GenkitMetric.FAITHFULNESS;
  judge: ModelReference<ModelCustomOptions>;
  judgeConfig?: z.infer<ModelCustomOptions>;
}

export interface MaliciousnessGenkitMetricConfig<
  ModelCustomOptions extends z.ZodTypeAny,
> extends BaseGenkitMetricConfig {
  type: GenkitMetric.MALICIOUSNESS;
  judge: ModelReference<ModelCustomOptions>;
  judgeConfig?: z.infer<ModelCustomOptions>;
}

export interface AnswerRelevancyGenkitMetricConfig<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
> extends BaseGenkitMetricConfig {
  type: GenkitMetric.ANSWER_RELEVANCY;
  judge: ModelReference<ModelCustomOptions>;
  judgeConfig?: z.infer<ModelCustomOptions>;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}
export type GenkitMetricConfig<
  M extends z.ZodTypeAny,
  E extends z.ZodTypeAny,
> =
  | FaithfulnessGenkitMetricConfig<M>
  | MaliciousnessGenkitMetricConfig<M>
  | AnswerRelevancyGenkitMetricConfig<M, E>;
