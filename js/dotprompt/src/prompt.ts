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
  PromptFrontmatter,
  PromptMetadata,
  toFrontmatter,
  toMetadata,
} from './metadata';
import { compile } from './template';
import {
  GenerationRequest,
  GenerationResponseSchema,
  MessageData,
} from '@genkit-ai/ai/model';
import fm, { FrontMatterResult } from 'front-matter';
import { GenerationResponse, generate } from '@genkit-ai/ai/generate';
import z from 'zod';
import { Action, action } from '@genkit-ai/common';
import { createHash } from 'crypto';
import { resolveTools, toToolDefinition } from '@genkit-ai/ai/tool';

const PromptInputSchema = z.object({
  variables: z.unknown().optional(),
  candidates: z.number().optional(),
});
export type PromptInput<Variables = unknown | undefined> = z.infer<
  typeof PromptInputSchema
> & {
  variables: Variables;
};

export type PromptData = PromptFrontmatter & { template: string };

export type PromptAction = Action<
  typeof PromptInputSchema,
  typeof GenerationResponseSchema,
  Record<string, unknown> & {
    type: 'prompt';
    prompt: PromptData;
  }
>;

export class Prompt<Variables = unknown> implements PromptMetadata {
  name: string;
  variant?: string;
  hash: string;

  template: string;

  model: PromptMetadata['model'];
  metadata: PromptMetadata['metadata'];
  input?: PromptMetadata['input'];
  output?: PromptMetadata['output'];
  tools?: PromptMetadata['tools'];
  config?: PromptMetadata['config'];

  private _render: (
    variables: Variables,
    options?: { context?: string[]; history?: MessageData[] }
  ) => MessageData[];

  private _action?: PromptAction;

  static parse(name: string, source: string) {
    const fmResult = (fm as any)(source) as FrontMatterResult<unknown>;
    return new Prompt(
      { ...toMetadata(fmResult.attributes), name } as PromptMetadata,
      fmResult.body
    );
  }

  static fromAction(action: PromptAction): Prompt {
    const { template, ...options } = action.__action.metadata!.prompt;
    const prompt = new Prompt(options as PromptMetadata, template);
    prompt._action = action;
    return prompt;
  }

  constructor(options: PromptMetadata, template: string) {
    this.name = options.name;
    this.variant = options.variant;
    this.model = options.model;
    this.input = options.input;
    this.output = options.output;
    this.tools = options.tools;
    this.config = options.config;
    this.template = template;
    this.hash = createHash('sha256').update(JSON.stringify(this)).digest('hex');

    // automatically assume supplied json schema is type: 'object' unless specified otherwise
    if (this.input?.jsonSchema && !(this.input?.jsonSchema as any).type) {
      (this.input.jsonSchema as any).type = 'object';
    }
    if (this.output?.jsonSchema && !(this.output?.jsonSchema as any).type) {
      (this.output.jsonSchema as any).type = 'object';
    }

    this._render = compile(this.template, options);
  }

  renderText(variables: Variables): string {
    const result = this.renderMessages(variables);
    if (result.length !== 1) {
      throw new Error("Multi-message prompt can't be rendered as text.");
    }
    let out = '';
    for (const part of result[0].content) {
      if (!part.text) {
        throw new Error("Multimodal prompt can't be rendered as text.");
      }
      out += part.text;
    }
    return out;
  }

  renderMessages(variables: Variables): MessageData[] {
    return this._render({ ...this.input?.default, ...variables });
  }

  async render(options: PromptInput<Variables>): Promise<GenerationRequest> {
    const messages = this.renderMessages(options.variables);
    return {
      config: this.config || {},
      messages,
      output: this.output || {},
      tools: (await resolveTools(this.tools)).map(toToolDefinition),
      candidates: options.candidates || 1,
    };
  }

  private _generate(
    options: PromptInput<Variables>
  ): Promise<GenerationResponse> {
    const messages = this.renderMessages(options.variables);
    return generate({
      model: this.model,
      config: this.config || {},
      history: messages.slice(0, messages.length - 1),
      prompt: messages[messages.length - 1].content,
      candidates: options.candidates || 1,
      output: {
        format: this.output?.format || undefined,
        schema: this.output?.schema,
        jsonSchema: this.output?.jsonSchema,
      },
    });
  }

  generate(options: PromptInput<Variables>): Promise<GenerationResponse> {
    return this.action()(options) as Promise<GenerationResponse>;
  }

  toJSON(): PromptData {
    return { ...toFrontmatter(this), template: this.template };
  }

  action(): PromptAction {
    if (this._action) return this._action;
    this._action = action(
      {
        name: `${this.name}${this.variant ? `.${this.variant}` : ''}`,
        input: PromptInputSchema,
        output: GenerationResponseSchema,
        metadata: {
          type: 'prompt',
          prompt: this.toJSON(),
        },
      },
      (input) => {
        return this._generate({
          variables: input.variables as Variables,
          candidates: input.candidates || 1,
        });
      }
    ) as PromptAction;
    return this._action;
  }
}
