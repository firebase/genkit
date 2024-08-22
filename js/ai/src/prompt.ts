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

import { Action, defineAction, JSONSchema7 } from '@genkit/core';
import { lookupAction } from '@genkit/core/registry';
import z from 'zod';
import { DocumentData } from './document.js';
import { GenerateOptions } from './generate.js';
import {
  GenerateRequest,
  GenerateRequestSchema,
  ModelArgument,
} from './model.js';

export type PromptFn<I extends z.ZodTypeAny = z.ZodTypeAny> = (
  input: z.infer<I>
) => Promise<GenerateRequest>;

export type PromptAction<I extends z.ZodTypeAny = z.ZodTypeAny> = Action<
  I,
  typeof GenerateRequestSchema
> & {
  __action: {
    metadata: {
      type: 'prompt';
    };
  };
};

export function isPrompt(arg: any): boolean {
  return (
    typeof arg === 'function' &&
    (arg as any).__action?.metadata?.type === 'prompt'
  );
}

export function definePrompt<I extends z.ZodTypeAny>(
  {
    name,
    description,
    inputSchema,
    inputJsonSchema,
    metadata,
  }: {
    name: string;
    description?: string;
    inputSchema?: I;
    inputJsonSchema?: JSONSchema7;
    metadata?: Record<string, any>;
  },
  fn: PromptFn<I>
): PromptAction<I> {
  const a = defineAction(
    {
      actionType: 'prompt',
      name,
      description,
      inputSchema,
      inputJsonSchema,
      metadata: { ...(metadata || { prompt: {} }), type: 'prompt' },
    },
    fn
  );
  return a as PromptAction<I>;
}

/**
 * A veneer for rendering a prompt action to GenerateOptions.
 */

export type PromptArgument<I extends z.ZodTypeAny = z.ZodTypeAny> =
  | string
  | PromptAction<I>;

export async function renderPrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(params: {
  prompt: PromptArgument<I>;
  input: z.infer<I>;
  context?: DocumentData[];
  model: ModelArgument<CustomOptions>;
  config?: z.infer<CustomOptions>;
}): Promise<GenerateOptions> {
  let prompt: PromptAction<I>;
  if (typeof params.prompt === 'string') {
    prompt = await lookupAction(`/prompt/${params.prompt}`);
  } else {
    prompt = params.prompt as PromptAction<I>;
  }
  const rendered = await prompt(params.input);
  return {
    model: params.model,
    config: { ...(rendered.config || {}), ...params.config },
    history: rendered.messages.slice(0, rendered.messages.length - 1),
    prompt: rendered.messages[rendered.messages.length - 1].content,
    context: params.context,
  };
}
