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

import {
  Action,
  ActionContext,
  ActionRunOptions,
  assertUnstable,
  defineAction,
  JSONSchema7,
  stripUndefinedProps,
  z,
} from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { parseSchema, toJsonSchema } from '@genkit-ai/core/schema';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import {
  Part,
  ToolDefinition,
  ToolRequestPart,
  ToolResponsePart,
} from './model.js';
import { ExecutablePrompt } from './prompt.js';

/**
 * An action with a `tool` type.
 */
export type ToolAction<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<C, I, O, z.ZodTypeAny, ToolRunOptions<C, z.infer<I>>> & {
  __action: {
    metadata: {
      type: 'tool';
    };
  };
  /**
   * respond constructs a tool response corresponding to the provided interrupt tool request
   * using the provided reply data, validating it against the output schema of the tool if
   * it exists.
   *
   * @beta
   */
  respond(
    /** The interrupt tool request to which you want to respond. */
    interrupt: ToolRequestPart,
    /**
     * The data with which you want to respond. Must conform to a tool's output schema or an
     * interrupt's input schema.
     **/
    outputData: z.infer<O>,
    options?: { metadata?: Record<string, any> }
  ): ToolResponsePart;

  /**
   * restart constructs a tool request corresponding to the provided interrupt tool request
   * that will then re-trigger the tool after e.g. a user confirms. The `resumedMetadata`
   * supplied to this method will be passed to the tool to allow for custom handling of
   * restart logic.
   *
   * @param interrupt The interrupt tool request you want to restart.
   * @param resumedMetadata The metadata you want to provide to the tool to aide in reprocessing. Defaults to `true` if none is supplied.
   * @param options Additional options for restarting the tool.
   *
   * @beta
   */
  restart(
    interrupt: ToolRequestPart,
    resumedMetadata?: any,
    options?: {
      /**
       * Replace the existing input arguments to the tool with different ones, for example
       * if the user revised an action before confirming. When input is replaced, the existing
       * tool request will be amended in the message history.
       **/
      replaceInput?: z.infer<I>;
    }
  ): ToolRequestPart;
};

export interface ToolRunOptions<
  C extends ActionContext = ActionContext,
  S = undefined,
> extends ActionRunOptions<C, S> {
  /**
   * If resumed is supplied to a tool at runtime, that means that it was previously interrupted and this is a second
   * @beta
   **/
  resumed?: boolean | Record<string, any>;
  /** The metadata from the tool request that triggered this run. */
  metadata?: Record<string, any>;
}

/**
 * Configuration for a tool.
 */
export interface ToolConfig<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  /** Unique name of the tool to use as a key in the registry. */
  name: string;
  /** Description of the tool. This is passed to the model to help understand what the tool is used for. */
  description: string;
  /** Input Zod schema. Mutually exclusive with `inputJsonSchema`. */
  inputSchema?: I;
  /** Input JSON schema. Mutually exclusive with `inputSchema`. */
  inputJsonSchema?: JSONSchema7;
  /** Output Zod schema. Mutually exclusive with `outputJsonSchema`. */
  outputSchema?: O;
  /** Output JSON schema. Mutually exclusive with `outputSchema`. */
  outputJsonSchema?: JSONSchema7;
  /** Metadata to be passed to the tool. */
  metadata?: Record<string, any>;
}

/**
 * A reference to a tool in the form of a name, definition, or the action itself.
 */
export type ToolArgument<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> = string | ToolAction<I, O> | Action<I, O> | ExecutablePrompt<any, any, any>;

/**
 * Converts an action to a tool action by setting the appropriate metadata.
 */
export function asTool<
  C extends ActionContext,
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
>(registry: Registry, action: Action<C, I, O>): ToolAction<C, I, O> {
  if (action.__action?.metadata?.type === 'tool') {
    return action as ToolAction<C, I, O>;
  }

  const fn = ((input) => {
    setCustomMetadataAttributes(registry, { subtype: 'tool' });
    return action(input);
  }) as ToolAction<C, I, O>;
  fn.__action = {
    ...action.__action,
    metadata: { ...action.__action.metadata, type: 'tool' },
  };
  return fn;
}

/**
 * Resolves a mix of various formats of tool references to a list of tool actions by looking them up in the registry.
 */
export async function resolveTools(
  registry: Registry,
  tools?: (ToolArgument | ToolDefinition)[]
): Promise<ToolAction[]> {
  if (!tools || tools.length === 0) {
    return [];
  }

  return await Promise.all(
    tools.map(async (ref): Promise<ToolAction> => {
      if (typeof ref === 'string') {
        return await lookupToolByName(registry, ref);
      } else if ((ref as Action).__action) {
        return asTool(registry, ref as Action);
      } else if (typeof (ref as ExecutablePrompt).asTool === 'function') {
        return await (ref as ExecutablePrompt).asTool();
      } else if (ref.name) {
        return await lookupToolByName(
          registry,
          (ref as ToolDefinition).metadata?.originalName || ref.name
        );
      }
      throw new Error('Tools must be strings, tool definitions, or actions.');
    })
  );
}

export async function lookupToolByName(
  registry: Registry,
  name: string
): Promise<ToolAction> {
  let tool =
    (await registry.lookupAction(name)) ||
    (await registry.lookupAction(`/tool/${name}`)) ||
    (await registry.lookupAction(`/prompt/${name}`));
  if (!tool) {
    throw new Error(`Tool ${name} not found`);
  }
  return tool as ToolAction;
}

/**
 * Converts a tool action to a definition of the tool to be passed to a model.
 */
export function toToolDefinition(
  tool: Action<z.ZodTypeAny, z.ZodTypeAny>
): ToolDefinition {
  const originalName = tool.__action.name;
  let name = originalName;
  if (originalName.includes('/')) {
    name = originalName.substring(originalName.lastIndexOf('/') + 1);
  }

  const out: ToolDefinition = {
    name,
    description: tool.__action.description || '',
    outputSchema: toJsonSchema({
      schema: tool.__action.outputSchema ?? z.void(),
      jsonSchema: tool.__action.outputJsonSchema,
    })!,
    inputSchema: toJsonSchema({
      schema: tool.__action.inputSchema ?? z.void(),
      jsonSchema: tool.__action.inputJsonSchema,
    })!,
  };

  if (originalName !== name) {
    out.metadata = { originalName };
  }

  return out;
}

export interface ToolFnOptions {
  /**
   * A function that can be called during tool execution that will result in the tool
   * getting interrupted (immediately) and tool request returned to the upstream caller.
   */
  interrupt: (metadata?: Record<string, any>) => never;

  context: ActionContext;
}

export type ToolFn<I extends z.ZodTypeAny, O extends z.ZodTypeAny> = (
  input: z.infer<I>,
  ctx: ToolFnOptions & ToolRunOptions
) => Promise<z.infer<O>>;

/**
 * Defines a tool.
 *
 * A tool is an action that can be passed to a model to be called automatically if it so chooses.
 */
export function defineTool<
  C extends ActionContext,
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
>(
  registry: Registry,
  config: ToolConfig<I, O>,
  fn: ToolFn<I, O>
): ToolAction<C, I, O> {
  const a = defineAction<C, I, O>(
    registry,
    {
      ...config,
      actionType: 'tool',
      metadata: { ...(config.metadata || {}), type: 'tool' },
    },
    (i, runOptions) => {
      return fn(i, {
        ...runOptions,
        context: { ...runOptions.context },
        interrupt: interruptTool(registry),
      });
    }
  ) as ToolAction<C, I, O>;
  a.respond = (interrupt, responseData, options) => {
    assertUnstable(
      registry,
      'beta',
      "The 'tool.reply' method is part of the 'interrupts' beta feature."
    );
    parseSchema(responseData, {
      jsonSchema: config.outputJsonSchema,
      schema: config.outputSchema,
    });
    return {
      toolResponse: stripUndefinedProps({
        name: interrupt.toolRequest.name,
        ref: interrupt.toolRequest.ref,
        output: responseData,
      }),
      metadata: {
        interruptResponse: options?.metadata || true,
      },
    };
  };

  a.restart = (interrupt, resumedMetadata, options) => {
    assertUnstable(
      registry,
      'beta',
      "The 'tool.restart' method is part of the 'interrupts' beta feature."
    );
    let replaceInput = options?.replaceInput;
    if (replaceInput) {
      replaceInput = parseSchema(replaceInput, {
        schema: config.inputSchema,
        jsonSchema: config.inputJsonSchema,
      });
    }
    return {
      toolRequest: stripUndefinedProps({
        name: interrupt.toolRequest.name,
        ref: interrupt.toolRequest.ref,
        input: replaceInput || interrupt.toolRequest.input,
      }),
      metadata: stripUndefinedProps({
        ...interrupt.metadata,
        resumed: resumedMetadata || true,
        // annotate the original input if replacing it
        replacedInput: replaceInput ? interrupt.toolRequest.input : undefined,
      }),
    };
  };
  return a;
}

/** InterruptConfig defines the options for configuring an interrupt. */
export type InterruptConfig<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  R extends z.ZodTypeAny = z.ZodTypeAny,
> = ToolConfig<I, R> & {
  /** requestMetadata adds additional `interrupt` metadata to the `toolRequest` generated by the interrupt */
  requestMetadata?:
    | Record<string, any>
    | ((
        input: z.infer<I>
      ) => Record<string, any> | Promise<Record<string, any>>);
};

export function isToolRequest(part: Part): part is ToolRequestPart {
  return !!part.toolRequest;
}

export function isToolResponse(part: Part): part is ToolResponsePart {
  return !!part.toolResponse;
}

export function defineInterrupt<
  C extends ActionContext,
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
>(registry: Registry, config: InterruptConfig<I, O>): ToolAction<C, I, O> {
  const { requestMetadata, ...toolConfig } = config;

  return defineTool<C, I, O>(
    registry,
    toolConfig,
    async (input, { interrupt }) => {
      if (!config.requestMetadata) interrupt();
      else if (typeof config.requestMetadata === 'object')
        interrupt(config.requestMetadata);
      else interrupt(await Promise.resolve(config.requestMetadata(input)));
    }
  );
}

/**
 * Thrown when tools execution is interrupted. It's meant to be caugh by the framework, not public API.
 */
export class ToolInterruptError extends Error {
  constructor(readonly metadata?: Record<string, any>) {
    super();
    this.name = 'ToolInterruptError';
  }
}

/**
 * Interrupts current tool execution causing tool request to be returned in the generation response.
 * Should only be called within a tool.
 */
function interruptTool(registry: Registry) {
  return (metadata?: Record<string, any>): never => {
    assertUnstable(registry, 'beta', 'Tool interrupts are a beta feature.');
    throw new ToolInterruptError(metadata);
  };
}
