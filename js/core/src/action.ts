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
import * as z from 'zod';
import { ActionType, Registry } from './registry.js';
import { parseSchema } from './schema.js';
import {
  SPAN_TYPE_ATTR,
  newTrace,
  setCustomMetadataAttributes,
} from './tracing.js';

export { Status, StatusCodes, StatusSchema } from './statusTypes.js';
export { JSONSchema7 };

export const GENKIT_SESSION_STATE_INPUT_KEY = '__genkit__sessionState';

export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
> {
  actionType?: ActionType;
  name: string;
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  outputSchema?: O;
  outputJsonSchema?: JSONSchema7;
  metadata?: M;
}

export type Action<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
> = ((input: z.infer<I>) => Promise<z.infer<O>>) & {
  __action: ActionMetadata<I, O, M>;
};

export type SideChannelData = Record<string, any>;

type ActionParams<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
> = {
  name:
    | string
    | {
        pluginId: string;
        actionId: string;
      };
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  outputSchema?: O;
  outputJsonSchema?: JSONSchema7;
  metadata?: M;
  use?: Middleware<z.infer<I>, z.infer<O>>[];
};

export interface Middleware<I = any, O = any> {
  (req: I, next: (req?: I) => Promise<O>): Promise<O>;
}

export function actionWithMiddleware<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
>(
  action: Action<I, O, M>,
  middleware: Middleware<z.infer<I>, z.infer<O>>[]
): Action<I, O, M> {
  const wrapped = (async (req: z.infer<I>) => {
    const dispatch = async (index: number, req: z.infer<I>) => {
      if (index === middleware.length) {
        // end of the chain, call the original model action
        return await action(req);
      }

      const currentMiddleware = middleware[index];
      return currentMiddleware(req, async (modifiedReq) =>
        dispatch(index + 1, modifiedReq || req)
      );
    };

    return await dispatch(0, req);
  }) as Action<I, O, M>;
  wrapped.__action = action.__action;
  return wrapped;
}

/**
 * Creates an action with the provided config.
 */
export function action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
>(
  config: ActionParams<I, O, M>,
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): Action<I, O> {
  const actionName =
    typeof config.name === 'string'
      ? config.name
      : `${config.name.pluginId}/${config.name.actionId}`;
  const actionFn = async (input: I) => {
    let sessionStateData: Record<string, any> | undefined = undefined;
    if (input?.hasOwnProperty(GENKIT_SESSION_STATE_INPUT_KEY)) {
      sessionStateData = input[GENKIT_SESSION_STATE_INPUT_KEY];
      input = { ...input };
      delete input[GENKIT_SESSION_STATE_INPUT_KEY];
    }
    input = parseSchema(input, {
      schema: config.inputSchema,
      jsonSchema: config.inputJsonSchema,
    });
    let output = await newTrace(
      {
        name: actionName,
        labels: {
          [SPAN_TYPE_ATTR]: 'action',
        },
      },
      async (metadata) => {
        metadata.name = actionName;
        metadata.input = input;

        if (sessionStateData) {
          input[GENKIT_SESSION_STATE_INPUT_KEY] = sessionStateData;
        }
        const output = await fn(input);

        metadata.output = JSON.stringify(output);
        return output;
      }
    );
    output = parseSchema(output, {
      schema: config.outputSchema,
      jsonSchema: config.outputJsonSchema,
    });
    return output;
  };
  actionFn.__action = {
    name: actionName,
    description: config.description,
    inputSchema: config.inputSchema,
    inputJsonSchema: config.inputJsonSchema,
    outputSchema: config.outputSchema,
    outputJsonSchema: config.outputJsonSchema,
    metadata: config.metadata,
  } as ActionMetadata<I, O, M>;

  if (config.use) {
    return actionWithMiddleware(actionFn, config.use);
  }
  return actionFn;
}

function validateActionName(registry: Registry, name: string) {
  if (name.includes('/')) {
    validatePluginName(registry, name.split('/', 1)[0]);
    validateActionId(name.substring(name.indexOf('/') + 1));
  }
  return name;
}

function validatePluginName(registry: Registry, pluginId: string) {
  if (!registry.lookupPlugin(pluginId)) {
    throw new Error(
      `Unable to find plugin name used in the action name: ${pluginId}`
    );
  }
  return pluginId;
}

function validateActionId(actionId: string) {
  if (actionId.includes('/')) {
    throw new Error(`Action name must not include slashes (/): ${actionId}`);
  }
  return actionId;
}

/**
 * Defines an action with the given config and registers it in the registry.
 */
export function defineAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>,
>(
  registry: Registry,
  config: ActionParams<I, O, M> & {
    actionType: ActionType;
  },
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): Action<I, O> {
  if (isInRuntimeContext()) {
    throw new Error(
      'Cannot define new actions at runtime.\n' +
        'See: https://github.com/firebase/genkit/blob/main/docs/errors/no_new_actions_at_runtime.md'
    );
  }
  if (typeof config.name === 'string') {
    validateActionName(registry, config.name);
  } else {
    validateActionId(config.name.actionId);
  }
  const act = action(config, async (i: I): Promise<z.infer<O>> => {
    setCustomMetadataAttributes({ subtype: config.actionType });
    await registry.initializeAllPlugins();
    return await runInActionRuntimeContext(() => fn(i));
  });
  act.__action.actionType = config.actionType;
  registry.registerAction(config.actionType, act);
  return act;
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

const runtimeCtxAls = new AsyncLocalStorage<any>();

/**
 * Checks whether the caller is currently in the runtime context of an action.
 */
export function isInRuntimeContext() {
  return !!runtimeCtxAls.getStore();
}

/**
 * Execute the provided function in the action runtime context.
 */
export function runInActionRuntimeContext<R>(fn: () => R) {
  return runtimeCtxAls.run('runtime', fn);
}
