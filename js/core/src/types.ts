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
import { AsyncLocalStorage } from 'node:async_hooks';
import { performance } from 'node:perf_hooks';
import * as z from 'zod';
import { parseSchema } from './schema.js';
import * as telemetry from './telemetry.js';
import { runInNewSpan, SPAN_TYPE_ATTR } from './tracing.js';

export { Status, StatusCodes, StatusSchema } from './statusTypes.js';
export { JSONSchema7 };

export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
> {
  name: string;
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  outputSchema?: O;
  outputJsonSchema?: JSONSchema7;
  metadata?: M;
}

export type Action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
> = ((input: z.infer<I>) => Promise<z.infer<O>>) & {
  __action: ActionMetadata<I, O, M>;
};

export type SideChannelData = Record<string, any>;

/**
 *
 */
export function action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
>(
  config: {
    name: string;
    description?: string;
    inputSchema?: I;
    inputJsonSchema?: JSONSchema7;
    outputSchema?: O;
    outputJsonSchema?: JSONSchema7;
    metadata?: M;
  },
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): Action<I, O> {
  const actionFn = async (input: I) => {
    input = parseSchema(input, {
      schema: config.inputSchema,
      jsonSchema: config.inputJsonSchema,
    });
    let output = await runInNewSpan(
      {
        metadata: {
          name: config.name,
        },
        labels: {
          [SPAN_TYPE_ATTR]: 'action',
        },
      },
      async (metadata) => {
        metadata.name = config.name;
        metadata.input = input;
        const startTimeMs = performance.now();
        try {
          const output = await fn(input);
          metadata.output = JSON.stringify(output);
          telemetry.writeActionSuccess(
            metadata.name,
            performance.now() - startTimeMs
          );
          return output;
        } catch (e) {
          telemetry.writeActionFailure(
            metadata.name,
            performance.now() - startTimeMs,
            e
          );
          throw e;
        }
      }
    );
    output = parseSchema(output, {
      schema: config.outputSchema,
      jsonSchema: config.outputJsonSchema,
    });
    return output;
  };
  actionFn.__action = {
    name: config.name,
    description: config.description,
    inputSchema: config.inputSchema,
    inputJsonSchema: config.inputJsonSchema,
    outputSchema: config.outputSchema,
    outputJsonSchema: config.outputJsonSchema,
    metadata: config.metadata,
  };
  return actionFn;
}

// Streaming callback function.
export type StreamingCallback<T> = (chunk: T) => void;

const streamingAls = new AsyncLocalStorage<StreamingCallback<any>>();
const sentinelNoopCallback = () => null;

/**
 * Executes provided function with streaming callback in async local storage which can be retrieved
 * using {@link getStreamingCallback}.
 */
export function runWithStreamingCallback<S, O>(
  streamingCallback: StreamingCallback<S> | undefined,
  fn: () => O
): O {
  return streamingAls.run(streamingCallback || sentinelNoopCallback, fn);
}

/**
 * Retrieves the {@link StreamingCallback} previously set by {@link runWithStreamingCallback}
 */
export function getStreamingCallback<S>(): StreamingCallback<S> | undefined {
  const cb = streamingAls.getStore();
  if (cb === sentinelNoopCallback) {
    return undefined;
  }
  return cb;
}
