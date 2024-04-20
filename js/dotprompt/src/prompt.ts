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
  generate,
  GenerateOptions,
  GenerateResponse,
  generateStream,
  GenerateStreamResponse,
} from '@genkit-ai/ai';
import {
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseSchema,
  GenerationCommonConfigSchema,
  MessageData,
} from '@genkit-ai/ai/model';
import { resolveTools, toToolDefinition } from '@genkit-ai/ai/tool';
import { Action, action, GenkitError } from '@genkit-ai/core';
import { JSONSchema, parseSchema, toJsonSchema } from '@genkit-ai/core/schema';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import { createHash } from 'crypto';
import fm, { FrontMatterResult } from 'front-matter';
import z from 'zod';
import {
  PromptFrontmatter,
  PromptMetadata,
  toFrontmatter,
  toMetadata,
} from './metadata.js';
import { compile } from './template.js';

const PromptActionInputSchema = GenerateRequestSchema.omit({
  messages: true,
  tools: true,
  output: true,
}).extend({
  model: z.string().optional(),
  input: z.unknown().optional(),
  tools: z.array(z.any()).optional(),
  output: z
    .object({
      format: z.enum(['json', 'text', 'media']).optional(),
      schema: z.any().optional(),
      jsonSchema: z.any().optional(),
    })
    .optional(),
});
export type PromptActionInput = z.infer<typeof PromptActionInputSchema>;

export type PromptGenerateOptions<V = unknown> = Omit<
  GenerateOptions<z.ZodTypeAny, typeof GenerationCommonConfigSchema>,
  'prompt' | 'history' | 'model'
> & {
  model?: string;
  input?: V;
};

export type PromptData = PromptFrontmatter & { template: string };

export type PromptAction = Action<
  typeof PromptActionInputSchema,
  typeof GenerateResponseSchema,
  Record<string, unknown> & {
    type: 'prompt';
    prompt: PromptData;
  }
>;

export class Prompt<Variables = unknown> implements PromptMetadata {
  name?: string;
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
    options?: { context?: string[]; history?: MessageData[] }
  ) => MessageData[];

  private _action?: PromptAction;

  static parse(name: string, source: string) {
    try {
      const fmResult = (fm as any)(source.trimStart(), {
        allowUnsafe: false,
      }) as FrontMatterResult<unknown>;

      return new Prompt(
        { ...toMetadata(fmResult.attributes), name } as PromptMetadata,
        fmResult.body
      );
    } catch (e: any) {
      throw new GenkitError({
        source: 'dotprompt',
        status: 'INVALID_ARGUMENT',
        message: `Error parsing YAML frontmatter of '${name}' prompt: ${e.message}`,
      });
    }
  }

  static fromAction(action: PromptAction): Prompt {
    const { template, ...options } = action.__action.metadata!.prompt;
    const pm = options as PromptMetadata;
    if (pm.input?.schema) {
      pm.input.jsonSchema = options.input?.schema;
      delete pm.input.schema;
    }
    if (pm.output?.schema) {
      pm.output.jsonSchema = options.output?.schema;
    }
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
    this.candidates = options.candidates;
    this.template = template;
    this.hash = createHash('sha256').update(JSON.stringify(this)).digest('hex');

    this._render = compile(this.template, options);
  }

  renderText(input: Variables): string {
    const result = this.renderMessages(input);
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

  renderMessages(input?: Variables): MessageData[] {
    input = parseSchema(input, {
      schema: this.input?.schema,
      jsonSchema: this.input?.jsonSchema,
    });
    return this._render({ ...this.input?.default, ...input });
  }

  async render(
    options: PromptGenerateOptions<Variables>
  ): Promise<GenerateRequest> {
    const messages = this.renderMessages(options.input);
    return {
      config: this.config || {},
      messages,
      output: this.output
        ? {
            format: this.output?.format,
            schema: toJsonSchema({
              schema: this.output?.schema,
              jsonSchema: this.output?.jsonSchema,
            }),
          }
        : {},
      tools: (await resolveTools(this.tools)).map(toToolDefinition),
      candidates: options.candidates || 1,
    };
  }

  private _generateOptions(
    options: PromptGenerateOptions<Variables>
  ): GenerateOptions {
    if (!options.model && !this.model) {
      throw new GenkitError({
        source: 'dotprompt',
        message: 'Must supply `model` in prompt metadata or generate options.',
        status: 'INVALID_ARGUMENT',
      });
    }

    const messages = this.renderMessages(options.input);
    return {
      model: options.model || this.model!,
      config: { ...this.config, ...options.config } || {},
      history: messages.slice(0, messages.length - 1),
      prompt: messages[messages.length - 1].content,
      candidates: options.candidates || this.candidates || 1,
      output: {
        format: options.output?.format || this.output?.format || undefined,
        schema: options.output?.schema || this.output?.schema,
        jsonSchema: options.output?.jsonSchema || this.output?.jsonSchema,
      },
    };
  }

  async _generate(req: PromptGenerateOptions<Variables>) {
    return generate(this._generateOptions(req));
  }

  async generate(
    options: PromptGenerateOptions<Variables>
  ): Promise<GenerateResponse> {
    const req = { ...options, tools: await resolveTools(options.tools) };
    return new GenerateResponse(
      await this.action()(req),
      await this.render(options) // TODO: don't re-render to do this
    );
  }

  async generateStream(
    options: PromptGenerateOptions<Variables>
  ): Promise<GenerateStreamResponse> {
    // TODO: properly wrap this in appropriate telemetry
    return generateStream(this._generateOptions(options));
  }

  toJSON(): PromptData {
    return { ...toFrontmatter(this), template: this.template };
  }

  action(): PromptAction {
    if (this._action) return this._action;

    this._action = action(
      {
        name: `${this.name}${this.variant ? `.${this.variant}` : ''}`,
        inputSchema: PromptActionInputSchema,
        outputSchema: GenerateResponseSchema,
        metadata: {
          type: 'prompt',
          prompt: this.toJSON(),
        },
      },
      (args) => {
        setCustomMetadataAttributes({ subtype: 'prompt' });
        args.output = args.output
          ? {
              format: args.output?.format,
              jsonSchema: toJsonSchema({
                schema: args.output.schema as z.ZodTypeAny,
                jsonSchema: args.output.jsonSchema as JSONSchema,
              }),
            }
          : undefined;
        return this._generate(args as PromptGenerateOptions<Variables>);
      }
    ) as PromptAction;
    const actionJsonSchema = toJsonSchema({
      schema: PromptActionInputSchema.omit({ input: true }),
    });
    if (this.input?.jsonSchema) {
      // Prompt file case
      (actionJsonSchema as any).properties.input = this.input.jsonSchema;
      this._action.__action.inputJsonSchema = actionJsonSchema;
    } else if (this.input?.schema) {
      // definePrompt case
      (actionJsonSchema as any).properties.input = toJsonSchema({
        schema: this.input.schema,
      });
      this._action.__action.inputJsonSchema = actionJsonSchema;
    }
    return this._action;
  }
}
