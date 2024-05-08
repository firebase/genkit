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

export function defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  {
    name,
    description,
    inputSchema,
    inputJsonSchema,
    outputSchema,
    outputJsonSchema,
    metadata,
  }: {
    name: string;
    description: string;
    inputSchema?: I;
    inputJsonSchema?: JSONSchema7;
    outputSchema?: O;
    outputJsonSchema?: JSONSchema7;
    metadata?: Record<string, any>;
  },
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): ToolAction<I, O> {
  const a = defineAction(
    {
      actionType: 'tool',
      name,
      description,
      inputSchema,
      inputJsonSchema,
      outputSchema,
      outputJsonSchema,
      metadata: { ...(metadata || {}), type: 'tool' },
    },
    (i) => fn(i)
  );
  return a as ToolAction<I, O>;
}
