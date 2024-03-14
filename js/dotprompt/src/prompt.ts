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

import { readFileSync } from 'fs';
import { PromptMetadata } from './metadata';
import { compile } from './template';
import {
  GenerationRequest,
  GenerationResponseSchema,
  MessageData,
} from '@genkit-ai/ai/model';
import fm from 'front-matter';
import { GenerationResponse, generate } from '@genkit-ai/ai/generate';
import z from 'zod';
import { Action, action } from '@genkit-ai/common';
import { createHash } from 'crypto';

const PromptInputSchema = z.object({
  variables: z.unknown().optional(),
  candidates: z.number().optional(),
});
export type PromptInput<Variables = unknown | undefined> = z.infer<
  typeof PromptInputSchema
> & {
  variables: Variables;
};

export type PromptAction = Action<
  typeof PromptInputSchema,
  typeof GenerationResponseSchema,
  Record<string, unknown> & {
    prompt: PromptOptions;
  }
>;

export interface PromptOptions {
  name: string;
  template: string;
  metadata: PromptMetadata;
  hash: string;
  variant?: string;
}

export class Prompt<Variables = unknown> {
  name: string;
  variant?: string;
  hash: string;
  metadata: PromptMetadata;
  template: string;

  private _render: (
    variables: Variables,
    options?: { context?: string[]; history?: MessageData[] }
  ) => MessageData[];

  private _action?: PromptAction;

  static parse(name: string, source: string) {
    const fmResult = (fm as any)(source);
    const hash = createHash('sha256').update(source).digest('hex');
    return new Prompt({
      name,
      hash,
      template: fmResult.body,
      metadata: fmResult.attributes as PromptMetadata,
    });
  }

  static fromAction(action: PromptAction): Prompt {
    const prompt = new Prompt(action.__action.metadata!.prompt);
    prompt._action = action;
    return prompt;
  }

  constructor(options: PromptOptions) {
    this.name = options.name;
    this.metadata = options.metadata;
    this.template = options.template;
    this.hash = options.hash;
    this.variant = options.variant;
    this._render = compile(this.template, this.metadata);
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
    return this._render(variables);
  }

  render(variables: Variables): GenerationRequest {
    const messages = this.renderMessages(variables);
    return {
      config: this.metadata.config || {},
      messages,
      output: this.metadata.output || {},
      // TODO: tools
      // TODO: candidates
    };
  }

  generate(options: PromptInput<Variables>): Promise<GenerationResponse> {
    const messages = this.renderMessages(options.variables);
    return generate({
      model: this.metadata.model,
      config: this.metadata.config || {},
      history: messages.slice(0, messages.length - 1),
      prompt: messages[messages.length - 1].content,
      candidates: options.candidates || 1,
      output: {
        format: this.metadata.output?.format || undefined,
        jsonSchema: this.metadata.output?.schema,
      },
    });
  }

  action(): PromptAction {
    if (this._action) return this._action;
    this._action = action(
      {
        name: `${this.name}${this.variant ? `.${this.variant}` : ''}`,
        input: PromptInputSchema,
        output: GenerationResponseSchema,
        metadata: {
          prompt: {
            name: this.name,
            template: this.template,
            metadata: this.metadata,
            hash: this.hash,
            variant: this.variant,
          },
        },
      },
      (input) => {
        return this.generate({
          variables: input.variables as Variables,
          candidates: input.candidates || 1,
        });
      }
    ) as PromptAction;
    return this._action;
  }
}
