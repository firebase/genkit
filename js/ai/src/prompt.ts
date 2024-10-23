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
import { DocumentData } from './document.js';
import {
  GenerateOptions,
  GenerateResponse,
  GenerateStreamResponse,
} from './generate.js';
import {
  GenerateRequest,
  GenerateRequestSchema,
  ModelArgument,
} from './model.js';
import { ToolAction } from './tool.js';

export type PromptFn<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> = (input: z.infer<I>) => Promise<GenerateRequest<CustomOptionsSchema>>;

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

/**
 * Configuration for a prompt action.
 */
export interface PromptConfig<I extends z.ZodTypeAny = z.ZodTypeAny> {
  name: string;
  description?: string;
  inputSchema?: I;
  inputJsonSchema?: JSONSchema7;
  metadata?: Record<string, any>;
}

export function isPrompt(arg: any): boolean {
  return (
    typeof arg === 'function' &&
    (arg as any).__action?.metadata?.type === 'prompt'
  );
}

export type PromptGenerateOptions<
  I = undefined,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<
  GenerateOptions<z.ZodTypeAny, CustomOptions>,
  'prompt' | 'input' | 'model'
> & {
  model?: ModelArgument<CustomOptions>;
  input?: I;
};

/**
 * A prompt that can be executed as a function.
 */
export interface ExecutablePrompt<
  I = undefined,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   *
   * @param input Prompt inputs.
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  <Out extends O>(
    input?: I,
    opts?: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateResponse<z.infer<Out>>>;

  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   * @param input Prompt inputs.
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  stream<Out extends O>(
    input?: I,
    opts?: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<Out>>>;

  /**
   * Generates a response by rendering the prompt template with given user input and additional generate options and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateResponse`.
   */
  generate<Out extends O>(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateResponse<z.infer<Out>>>;

  /**
   * Generates a streaming response by rendering the prompt template with given user input and additional generate options and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  generateStream<Out extends O>(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<Out>>>;

  /**
   * Renders the prompt template based on user input.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns a `GenerateOptions` object to be used with the `generate()` function from @genkit-ai/ai.
   */
  render<Out extends O>(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateOptions<CustomOptions, Out>>;

  /**
   * Returns the prompt usable as a tool.
   */
  asTool(): ToolAction;
}

/**
 * Defines and registers a prompt action. The action can be called to obtain
 * a `GenerateRequest` which can be passed to a model action. The given
 * `PromptFn` can perform any action needed to create the request such as rendering
 * a template or fetching a prompt from a database.
 *
 * @returns The new `PromptAction`.
 */
export function definePrompt<I extends z.ZodTypeAny>(
  registry: Registry,
  config: PromptConfig<I>,
  fn: PromptFn<I>
): PromptAction<I> {
  const a = defineAction(
    registry,
    {
      ...config,
      actionType: 'prompt',
      metadata: { ...(config.metadata || { prompt: {} }), type: 'prompt' },
    },
    fn
  );
  return a as PromptAction<I>;
}

export type PromptArgument<I extends z.ZodTypeAny = z.ZodTypeAny> =
  | string
  | PromptAction<I>;

/**
 * This veneer renders a `PromptAction` into a `GenerateOptions` object.
 *
 * @returns A promise of an options object for use with the `generate()` function.
 */
export async function renderPrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  params: {
    prompt: PromptArgument<I>;
    input: z.infer<I>;
    docs?: DocumentData[];
    model: ModelArgument<CustomOptions>;
    config?: z.infer<CustomOptions>;
  }
): Promise<GenerateOptions<O, CustomOptions>> {
  let prompt: PromptAction<I>;
  if (typeof params.prompt === 'string') {
    prompt = await registry.lookupAction(`/prompt/${params.prompt}`);
  } else {
    prompt = params.prompt as PromptAction<I>;
  }
  const rendered = (await prompt(
    params.input
  )) as GenerateRequest<CustomOptions>;
  return {
    model: params.model,
    config: { ...(rendered.config || {}), ...params.config },
    messages: rendered.messages.slice(0, rendered.messages.length - 1),
    prompt: rendered.messages[rendered.messages.length - 1].content,
    docs: params.docs,
    output: {
      format: rendered.output?.format,
      schema: rendered.output?.schema,
    },
    tools: rendered.tools || [],
  } as GenerateOptions<O, CustomOptions>;
}
