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

import { JSONSchema7 } from 'json-schema';
import * as z from 'zod';

// TODO: Temporarily here to get rid of the dependency on @genkit-ai/common.
// This will be replaced with a better interface.
export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> {
  name: string;
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  outputSchema?: unknown;
  outputJsonSchema?: JSONSchema7;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
}

export class GenkitToolsError extends Error {
  public data?: Record<string, unknown>;

  constructor(msg: string, options?: ErrorOptions) {
    super(msg, options);
  }
}

// Streaming callback function.
export type StreamingCallback<T> = (chunk: T) => void;
