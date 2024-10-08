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

export const GENKIT_VERSION = version;
export const GENKIT_CLIENT_HEADER = `genkit-node/${GENKIT_VERSION} gl-node/${process.versions.node}`;

export { z } from 'zod';
export * from './action.js';
export { getFlowAuth } from './auth.js';
export { GenkitError } from './error.js';
export {
  Flow,
  FlowServer,
  defineFlow,
  defineStreamingFlow,
  run,
  type CallableFlow,
  type FlowAuthPolicy,
  type FlowConfig,
  type FlowFn,
  type FlowServerOptions,
  type StreamableFlow,
  type StreamingFlowConfig,
  type __RequestWithAuth,
} from './flow.js';
export * from './flowTypes.js';
export * from './plugin.js';
export * from './reflection.js';
export { defineJsonSchema, defineSchema, type JSONSchema } from './schema.js';
export * from './telemetryTypes.js';
export * from './utils.js';
