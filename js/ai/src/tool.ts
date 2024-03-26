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

import { Action, action } from '@genkit-ai/common';
import { lookupAction, registerAction } from '@genkit-ai/common/registry';
import { setCustomMetadataAttributes } from '@genkit-ai/common/tracing';
import z from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';
import { ToolDefinition } from './model';

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
> = string | ToolAction<I, O> | Action<I, O>;

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
>(
  tools: (Action<z.ZodTypeAny, z.ZodTypeAny> | string)[] = []
): Promise<ToolAction[]> {
  return await Promise.all(
    tools.map(async (ref): Promise<ToolAction> => {
      if (typeof ref === 'string') {
        const tool = await lookupAction(`/tool/${ref}`);
        if (!tool) {
          throw new Error(`Tool ${ref} not found`);
        }
        return tool as ToolAction;
      } else if (ref.__action) {
        return asTool(ref);
      }
      throw new Error('Tools must be strings or actions.');
    })
  );
}

export function toToolDefinition(
  tool: Action<z.ZodTypeAny, z.ZodTypeAny>
): ToolDefinition {
  return {
    name: tool.__action.name,
    description: tool.__action.description || '',
    outputSchema: tool.__action.outputSchema
      ? zodToJsonSchema(tool.__action.outputSchema)
      : {}, // JSON schema matching anything
    inputSchema: zodToJsonSchema(tool.__action.inputSchema!),
  };
}

export function defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  {
    name,
    description,
    input,
    output,
    metadata,
  }: {
    name: string;
    description: string;
    input?: I;
    output?: O;
    metadata?: Record<string, any>;
  },
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): ToolAction<I, O> {
  const a = action(
    {
      name,
      description,
      input,
      output,
      metadata: { ...(metadata || {}), type: 'tool' },
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'tool' });
      return fn(i);
    }
  );
  registerAction('tool', name, a);
  return a as ToolAction<I, O>;
}
