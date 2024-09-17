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

import { Action, defineAction, JSONSchema7 } from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import z from 'zod';
import { ToolDefinition } from './model.js';

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

export type ToolArgument<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> = string | ToolAction<I, O> | Action<I, O> | ToolDefinition;

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
 * Takes one or more references to tools in various formats and resolves them to a list of tool actions.
 */
export async function resolveTools<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(tools: ToolArgument[] = []): Promise<ToolAction[]> {
  return await Promise.all(
    tools.map(async (ref): Promise<ToolAction> => {
      if (typeof ref === 'string') {
        const tool = await lookupAction(`/tool/${ref}`);
        if (!tool) {
          throw new Error(`Tool ${ref} not found`);
        }
        return tool as ToolAction;
      } else if ((ref as Action).__action) {
        return asTool(ref as Action);
      } else if (ref.name) {
        const tool = await lookupAction(`/tool/${ref.name}`);
        if (!tool) {
          throw new Error(`Tool ${ref} not found`);
        }
      }
      throw new Error('Tools must be strings, tool definitions, or actions.');
    })
  );
}

/**
 * Converts an action to a tool definition.
 */
export function toToolDefinition(
  tool: Action<z.ZodTypeAny, z.ZodTypeAny>
): ToolDefinition {
  return {
    name: tool.__action.name,
    description: tool.__action.description || '',
    outputSchema: toJsonSchema({
      schema: tool.__action.outputSchema,
      jsonSchema: tool.__action.outputJsonSchema,
    })!,
    inputSchema: toJsonSchema({
      schema: tool.__action.inputSchema,
      jsonSchema: tool.__action.inputJsonSchema,
    })!,
  };
}

/**
 * Configuration for a tool to be used in a call to a model.
 */
export interface ToolConfig<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  /** Name of the tool. */
  name: string;
  /** Description. This is used to describe the tool's purpose to the model. */
  description: string;
  /** Input schema. */
  inputSchema?: I;
  /** Input schema as JSON Schema. */
  inputJsonSchema?: JSONSchema7;
  /** Output schema. */
  outputSchema?: O;
  /** Output schema as JSON Schema. */
  outputJsonSchema?: JSONSchema7;
  /** Metadata for the tool. */
  metadata?: Record<string, any>;
}

/**
 * Defines a tool to be used in a call to a model.
 */
export function defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  config: ToolConfig<I, O>,
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): ToolAction<I, O> {
  const a = defineAction(
    {
      actionType: 'tool',
      name: config.name,
      description: config.description,
      inputSchema: config.inputSchema,
      inputJsonSchema: config.inputJsonSchema,
      outputSchema: config.outputSchema,
      outputJsonSchema: config.outputJsonSchema,
      metadata: { ...(config.metadata || {}), type: 'tool' },
    },
    (i) => fn(i)
  );
  return a as ToolAction<I, O>;
}
