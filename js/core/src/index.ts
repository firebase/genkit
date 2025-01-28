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

import { version } from './__codegen/version.js';

/**
 * Genkit library version.
 */
export const GENKIT_VERSION = version;

/**
 * Genkit client header for API calls.
 */
export const GENKIT_CLIENT_HEADER = `genkit-node/${GENKIT_VERSION} gl-node/${process.versions.node}`;
export const GENKIT_REFLECTION_API_SPEC_VERSION = 1;

export { z } from 'zod';
export * from './action.js';
export { getContext, runWithContext, type ActionContext } from './context.js';
export { GenkitError } from './error.js';
export {
  defineFlow,
  run,
  type Flow,
  type FlowConfig,
  type FlowFn,
} from './flow.js';
export * from './plugin.js';
export * from './reflection.js';
export { defineJsonSchema, defineSchema, type JSONSchema } from './schema.js';
export * from './telemetryTypes.js';
export * from './utils.js';
