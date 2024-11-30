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

/**
 * Action metadata.
 */
export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
> {
  actionType?: ActionType;
  name: string;
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  outputSchema?: O;
  outputJsonSchema?: JSONSchema7;
  streamSchema?: S;
  metadata?: Record<string, any>;
}

/**
 * Results of an action run. Includes telemetry.
 */
export interface ActionResult<O> {
  result: O;
  telemetry: {
    traceId: string;
    spanId: string;
  };
}

/**
 * Options (side channel) data to pass to the model.
 */
export interface ActionRunOptions<S> {
  /**
   * Streaming callback (optional).
   */
  onChunk?: StreamingCallback<S>;

  /**
   * Additional runtime context data (ex. auth context data).
   */
  context?: any;
}

/**
 * Options (side channel) data to pass to the model.
 */
export interface ActionFnArg<S> {
  /**
   * Streaming callback (optional).
   */
  sendChunk: StreamingCallback<S>;

  /**
   * Additional runtime context data (ex. auth context data).
   */
  context?: any;
}

/**
 * Self-describing, validating, observable, locally and remotely callable function.
 */
export type Action<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = ((
  input: z.infer<I>,
  options?: ActionRunOptions<S>
) => Promise<z.infer<O>>) & {
  __action: ActionMetadata<I, O, S>;
  run(
    input: z.infer<I>,
    options?: ActionRunOptions<z.infer<S>>
  ): Promise<ActionResult<z.infer<O>>>;
};

/**
 * Action factory params.
 */
type ActionParams<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
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
  metadata?: Record<string, any>;
  use?: Middleware<z.infer<I>, z.infer<O>, z.infer<S>>[];
  streamingSchema?: S;
};

export type SimpleMiddleware<I = any, O = any> = (
  req: I,
  next: (req?: I) => Promise<O>
) => Promise<O>;

export type MiddlewareWithOptions<I = any, O = any, S = any> = (
  req: I,
  options: ActionRunOptions<S> | undefined,
  next: (req?: I, options?: ActionRunOptions<S>) => Promise<O>
) => Promise<O>;

/**
 * Middleware function for actions.
 */
export type Middleware<I = any, O = any, S = any> =
  | SimpleMiddleware<I, O>
  | MiddlewareWithOptions<I, O, S>;

/**
 * Creates an action with provided middleware.
 */
export function actionWithMiddleware<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  action: Action<I, O, S>,
  middleware: Middleware<z.infer<I>, z.infer<O>, z.infer<S>>[]
): Action<I, O, S> {
  const wrapped = (async (req: z.infer<I>) => {
    return (await wrapped.run(req)).result;
  }) as Action<I, O, S>;
  wrapped.__action = action.__action;
  wrapped.run = async (
    req: z.infer<I>,
    options?: ActionRunOptions<z.infer<S>>
  ): Promise<ActionResult<z.infer<O>>> => {
    let telemetry;
    const dispatch = async (
      index: number,
      req: z.infer<I>,
      opts?: ActionRunOptions<z.infer<S>>
    ) => {
      if (index === middleware.length) {
        // end of the chain, call the original model action
        const result = await action.run(req, opts);
        telemetry = result.telemetry;
        return result.result;
      }

      const currentMiddleware = middleware[index];
      if (currentMiddleware.length === 3) {
        return (currentMiddleware as MiddlewareWithOptions<I, O, z.infer<S>>)(
          req,
          opts,
          async (modifiedReq, modifiedOptions) =>
            dispatch(index + 1, modifiedReq || req, modifiedOptions || opts)
        );
      } else if (currentMiddleware.length === 2) {
        return (currentMiddleware as SimpleMiddleware<I, O>)(
          req,
          async (modifiedReq) => dispatch(index + 1, modifiedReq || req, opts)
        );
      } else {
        throw new Error('unspported middleware function shape');
      }
    };

    return { result: await dispatch(0, req, options), telemetry };
  };
  return wrapped;
}

/**
 * Creates an action with the provided config.
 */
export function action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  config: ActionParams<I, O, S>,
  fn: (
    input: z.infer<I>,
    options: ActionFnArg<z.infer<S>>
  ) => Promise<z.infer<O>>
): Action<I, O, z.infer<S>> {
  const actionName =
    typeof config.name === 'string'
      ? config.name
      : `${config.name.pluginId}/${config.name.actionId}`;
  const actionFn = async (input: I, options?: ActionRunOptions<z.infer<S>>) => {
    return (await actionFn.run(input, options)).result;
  };
  actionFn.__action = {
    name: actionName,
    description: config.description,
    inputSchema: config.inputSchema,
    inputJsonSchema: config.inputJsonSchema,
    outputSchema: config.outputSchema,
    outputJsonSchema: config.outputJsonSchema,
    metadata: config.metadata,
  } as ActionMetadata<I, O, S>;
  actionFn.run = async (
    input: z.infer<I>,
    options?: ActionRunOptions<z.infer<S>>
  ): Promise<ActionResult<z.infer<O>>> => {
    input = parseSchema(input, {
      schema: config.inputSchema,
      jsonSchema: config.inputJsonSchema,
    });
    let traceId;
    let spanId;
    let output = await newTrace(
      {
        name: actionName,
        labels: {
          [SPAN_TYPE_ATTR]: 'action',
        },
      },
      async (metadata, span) => {
        traceId = span.spanContext().traceId;
        spanId = span.spanContext().spanId;
        metadata.name = actionName;
        metadata.input = input;

        const output = await fn(input, {
          context: options?.context,
          sendChunk: options?.onChunk ?? ((c) => {}),
        });

        metadata.output = JSON.stringify(output);
        return output;
      }
    );
    output = parseSchema(output, {
      schema: config.outputSchema,
      jsonSchema: config.outputJsonSchema,
    });
    return {
      result: output,
      telemetry: {
        traceId,
        spanId,
      },
    };
  };

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
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  config: ActionParams<I, O, S> & {
    actionType: ActionType;
  },
  fn: (
    input: z.infer<I>,
    options: ActionFnArg<z.infer<S>>
  ) => Promise<z.infer<O>>
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
  const act = action(config, async (i: I, options): Promise<z.infer<O>> => {
    setCustomMetadataAttributes({ subtype: config.actionType });
    await registry.initializeAllPlugins();
    return await runInActionRuntimeContext(() => fn(i, options));
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
