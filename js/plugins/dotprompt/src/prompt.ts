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
  definePrompt,
  generate,
  GenerateOptions,
  GenerateResponse,
  generateStream,
  GenerateStreamResponse,
  PromptAction,
  toGenerateRequest,
} from '@genkit-ai/ai';
import { GenerationCommonConfigSchema, MessageData } from '@genkit-ai/ai/model';
import { DocumentData } from '@genkit-ai/ai/retriever';
import { GenkitError } from '@genkit-ai/core';
import { parseSchema } from '@genkit-ai/core/schema';
import { createHash } from 'crypto';
import fm, { FrontMatterResult } from 'front-matter';
import z from 'zod';
import {
  PromptFrontmatter,
  PromptMetadata,
  toFrontmatter,
  toMetadata,
} from './metadata.js';
import { registryDefinitionKey } from './registry.js';
import { compile } from './template.js';

export type PromptData = PromptFrontmatter & { template: string };

export type PromptGenerateOptions<V = unknown> = Omit<
  GenerateOptions<z.ZodTypeAny, typeof GenerationCommonConfigSchema>,
  'prompt' | 'model'
> & {
  model?: string;
  input?: V;
};

interface RenderMetadata {
  context?: DocumentData[];
  history?: MessageData[];
}

export class Dotprompt<Variables = unknown> implements PromptMetadata {
  name: string;
  variant?: string;
  hash: string;

  template: string;

  model?: PromptMetadata['model'];
  metadata: PromptMetadata['metadata'];
  input?: PromptMetadata['input'];
  output?: PromptMetadata['output'];
  tools?: PromptMetadata['tools'];
  config?: PromptMetadata['config'];
  candidates?: PromptMetadata['candidates'];

  private _render: (
    input: Variables,
    options?: RenderMetadata
  ) => MessageData[];

  static parse(name: string, source: string) {
    try {
      const fmResult = (fm as any)(source.trimStart(), {
        allowUnsafe: false,
      }) as FrontMatterResult<unknown>;

      return new Dotprompt(
        { ...toMetadata(fmResult.attributes), name } as PromptMetadata,
        fmResult.body
      );
    } catch (e: any) {
      throw new GenkitError({
        source: 'Dotprompt',
        status: 'INVALID_ARGUMENT',
        message: `Error parsing YAML frontmatter of '${name}' prompt: ${e.stack}`,
      });
    }
  }

  static fromAction(action: PromptAction): Dotprompt {
    const { template, ...options } = action.__action.metadata!.prompt;
    const pm = options as PromptMetadata;
    if (pm.input?.schema) {
      pm.input.jsonSchema = options.input?.schema;
      delete pm.input.schema;
    }
    if (pm.output?.schema) {
      pm.output.jsonSchema = options.output?.schema;
    }
    const prompt = new Dotprompt(options as PromptMetadata, template);
    return prompt;
  }

  constructor(options: PromptMetadata, template: string) {
    this.name = options.name || 'untitledPrompt';
    this.variant = options.variant;
    this.model = options.model;
    this.input = options.input || { schema: z.any() };
    this.output = options.output;
    this.tools = options.tools;
    this.config = options.config;
    this.candidates = options.candidates;
    this.template = template;
    this.hash = createHash('sha256').update(JSON.stringify(this)).digest('hex');

    this._render = compile(this.template, options);
  }

  renderText(input: Variables, options?: RenderMetadata): string {
    const result = this.renderMessages(input, options);
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

  renderMessages(input?: Variables, options?: RenderMetadata): MessageData[] {
    input = parseSchema(input, {
      schema: this.input?.schema,
      jsonSchema: this.input?.jsonSchema,
    });
    return this._render({ ...this.input?.default, ...input }, options);
  }

  toJSON(): PromptData {
    return { ...toFrontmatter(this), template: this.template };
  }

  define(options?: { ns: string }): void {
    definePrompt(
      {
        name: registryDefinitionKey(this.name, this.variant, options?.ns),
        description: 'Defined by Dotprompt',
        inputSchema: this.input?.schema,
        inputJsonSchema: this.input?.jsonSchema,
        metadata: {
          type: 'prompt',
          prompt: this.toJSON(),
        },
      },
      async (input?: Variables) => toGenerateRequest(this.render({ input }))
    );
  }

  private _generateOptions<O extends z.ZodTypeAny = z.ZodTypeAny>(
    options: PromptGenerateOptions<Variables>
  ): GenerateOptions<z.ZodTypeAny, O> {
    const messages = this.renderMessages(options.input, {
      history: options.history,
      context: options.context,
    });
    return {
      model: options.model || this.model!,
      config: { ...this.config, ...options.config } || {},
      history: messages.slice(0, messages.length - 1),
      prompt: messages[messages.length - 1].content,
      context: options.context,
      candidates: options.candidates || this.candidates || 1,
      output: {
        format: options.output?.format || this.output?.format || undefined,
        schema: options.output?.schema || this.output?.schema,
        jsonSchema: options.output?.jsonSchema || this.output?.jsonSchema,
      },
      tools: (options.tools || []).concat(this.tools || []),
      streamingCallback: options.streamingCallback,
      returnToolRequests: options.returnToolRequests,
    } as GenerateOptions<z.ZodTypeAny, O>;
  }

  render<O extends z.ZodTypeAny = z.ZodTypeAny>(
    opt: PromptGenerateOptions<Variables>
  ): GenerateOptions<z.ZodTypeAny, O> {
    return this._generateOptions<O>(opt);
  }

  async generate<O extends z.ZodTypeAny = z.ZodTypeAny>(
    opt: PromptGenerateOptions<Variables>
  ): Promise<GenerateResponse<O>> {
    return generate<z.ZodTypeAny, O>(this.render<O>(opt));
  }

  async generateStream(
    opt: PromptGenerateOptions<Variables>
  ): Promise<GenerateStreamResponse> {
    return generateStream(this.render(opt));
  }
}

export function defineDotprompt<V extends z.ZodTypeAny = z.ZodTypeAny>(
  options: PromptMetadata<V>,
  template: string
): Dotprompt<z.infer<V>> {
  const prompt = new Dotprompt(options, template);
  prompt.define();
  return prompt;
}
