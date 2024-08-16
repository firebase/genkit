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

import { DatasetStore, EvalStore } from '../types/eval';
import { LocalFileDatasetStore } from './localFileDatasetStore';
import { LocalFileEvalStore } from './localFileEvalStore';
export { EvalFlowInput, EvalFlowInputSchema } from '../types/eval';
export * from './exporter';
export * from './parser';

export function getEvalStore(): EvalStore {
  // TODO: This should provide EvalStore, based on tools config.
  return LocalFileEvalStore.getEvalStore();
}

export function getDatasetStore(): DatasetStore {
  return LocalFileDatasetStore.getDatasetStore();
}
