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

import { Action, defineAction, JSONSchema7, z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import { ToolDefinition } from './model.js';
import { ExecutablePrompt } from './prompt.js';

/**
 * An action with a `tool` type.
 */
export type ToolAction<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<I, O> & {
  __action: {
    metadata: {
      type: 'tool';
    };
  };
};

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
> =
  | string
  | ToolAction<I, O>
  | Action<I, O>
  | ToolDefinition
  | ExecutablePrompt<any, any, any>;

/**
 * Converts an action to a tool action by setting the appropriate metadata.
 */
export function asTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  action: Action<I, O>
): ToolAction<I, O> {
  if (action.__action?.metadata?.type === 'tool') {
    return action as ToolAction<I, O>;
  }

  const fn = ((input) => {
    setCustomMetadataAttributes({ subtype: 'tool' });
    return action(input);
  }) as ToolAction<I, O>;
  fn.__action = {
    ...action.__action,
    metadata: { ...action.__action.metadata, type: 'tool' },
  };
  return fn;
}

/**
 * Resolves a mix of various formats of tool references to a list of tool actions by looking them up in the registry.
 */
export async function resolveTools<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(registry: Registry, tools?: ToolArgument[]): Promise<ToolAction[]> {
  if (!tools || tools.length === 0) {
    return [];
  }

  return await Promise.all(
    tools.map(async (ref): Promise<ToolAction> => {
      if (typeof ref === 'string') {
        return await lookupToolByName(registry, ref);
      } else if ((ref as Action).__action) {
        return asTool(ref as Action);
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

/**
 * Defines a tool.
 *
 * A tool is an action that can be passed to a model to be called automatically if it so chooses.
 */
export function defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  registry: Registry,
  config: ToolConfig<I, O>,
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): ToolAction<I, O> {
  const a = defineAction(
    registry,
    {
      ...config,
      actionType: 'tool',
      metadata: { ...(config.metadata || {}), type: 'tool' },
    },
    (i) => fn(i)
  );
  return a as ToolAction<I, O>;
}
