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
import { MessageData, ModelArgument } from '@genkit-ai/ai/model';
import { DocumentData } from '@genkit-ai/ai/retriever';
import { getCurrentSession } from '@genkit-ai/ai/session';
import { GenkitError, z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { parseSchema } from '@genkit-ai/core/schema';
import {
  runInNewSpan,
  setCustomMetadataAttribute,
  SPAN_TYPE_ATTR,
} from '@genkit-ai/core/tracing';
import { createHash } from 'crypto';
import fm, { FrontMatterResult } from 'front-matter';
import {
  PromptFrontmatter,
  PromptMetadata,
  toFrontmatter,
  toMetadata,
} from './metadata.js';
import { lookupPrompt, registryDefinitionKey } from './registry.js';
import { compile } from './template.js';

export type PromptData = PromptFrontmatter & { template: string };

export type PromptGenerateOptions<
  V = unknown,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<
  GenerateOptions<z.ZodTypeAny, CustomOptions>,
  'prompt' | 'input' | 'model'
> & {
  model?: ModelArgument<CustomOptions>;
  input?: V;
};

interface RenderMetadata {
  docs?: DocumentData[];
  messages?: MessageData[];
}

export class Dotprompt<I = unknown> implements PromptMetadata<z.ZodTypeAny> {
  name: string;
  description?: string;
  variant?: string;
  hash: string;

  template: string;

  model?: PromptMetadata['model'];
  metadata: PromptMetadata['metadata'];
  input?: PromptMetadata['input'];
  output?: PromptMetadata['output'];
  tools?: PromptMetadata['tools'];
  config?: PromptMetadata['config'];

  private _promptAction?: PromptAction;

  private _render: (
    input: I,
    options?: RenderMetadata,
    data?: Record<string, any>
  ) => MessageData[];

  static parse(registry: Registry, name: string, source: string) {
    try {
      const fmResult = (fm as any)(source.trimStart(), {
        allowUnsafe: false,
      }) as FrontMatterResult<unknown>;

      return new Dotprompt(
        registry,
        {
          ...toMetadata(registry, fmResult.attributes),
          name,
        } as PromptMetadata,
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

  static fromAction(registry: Registry, action: PromptAction): Dotprompt {
    const { template, ...options } = action.__action.metadata!.prompt;
    const pm = options as PromptMetadata;
    if (pm.input?.schema) {
      pm.input.jsonSchema = options.input?.schema;
      delete pm.input.schema;
    }
    if (pm.output?.schema) {
      pm.output.jsonSchema = options.output?.schema;
    }
    const prompt = new Dotprompt(
      registry,
      options as PromptMetadata,
      template,
      action
    );
    return prompt;
  }

  constructor(
    private registry: Registry,
    options: PromptMetadata,
    template: string,
    action?: PromptAction
  ) {
    this.name = options.name || 'untitledPrompt';
    this.description = options.description;
    this.variant = options.variant;
    this.model = options.model;
    this.input = options.input || { schema: z.any() };
    this.output = options.output;
    this.tools = options.tools;
    this.config = options.config;
    this.template = template;
    this.hash = createHash('sha256').update(JSON.stringify(this)).digest('hex');

    this._render = compile(this.template, options);
    this._promptAction = action;
  }

  /**
   * Renders all of the prompt's text parts into a raw string.
   *
   * @param input User input to the prompt template.
   * @param options Optional context and/or history for the prompt template.
   * @returns all of the text parts concatenated into a string.
   */

  renderText(input: I, options?: RenderMetadata): string {
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

  /**
   * Renders the prompt template into an array of messages.
   *
   * @param input User input to the prompt template
   * @param options optional context and/or history for the prompt template.
   * @returns an array of messages representing an exchange between a user and a model.
   */
  renderMessages(input?: I, options?: RenderMetadata): MessageData[] {
    let sessionStateData: Record<string, any> | undefined = undefined;
    if (getCurrentSession()) {
      sessionStateData = { state: getCurrentSession()?.state };
    }
    input = parseSchema(input, {
      schema: this.input?.schema,
      jsonSchema: this.input?.jsonSchema,
    });
    return this._render(
      { ...this.input?.default, ...input },
      options,
      sessionStateData
    );
  }

  toJSON(): PromptData {
    return { ...toFrontmatter(this), template: this.template };
  }

  define(options?: { ns?: string; description?: string }): void {
    this._promptAction = definePrompt(
      this.registry,
      {
        name: registryDefinitionKey(this.name, this.variant, options?.ns),
        description: options?.description ?? this.description,
        inputSchema: this.input?.schema,
        inputJsonSchema: this.input?.jsonSchema,
        metadata: {
          type: 'prompt',
          prompt: this.toJSON(),
        },
      },
      async (input?: I) =>
        toGenerateRequest(this.registry, this.render({ input }))
    );
  }

  get promptAction(): PromptAction | undefined {
    return this._promptAction;
  }

  private _generateOptions<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(options: PromptGenerateOptions<I>): GenerateOptions<O, CustomOptions> {
    const messages = this.renderMessages(options.input, {
      messages: options.messages,
      docs: options.docs,
    });
    let renderedPrompt;
    let renderedMessages;
    if (messages.length > 0 && messages[messages.length - 1].role === 'user') {
      renderedPrompt = messages[messages.length - 1].content;
      renderedMessages = messages.slice(0, messages.length - 1);
    } else {
      renderedPrompt = undefined;
      renderedMessages = messages;
    }
    return {
      model: options.model || this.model!,
      config: { ...this.config, ...options.config },
      messages: renderedMessages,
      prompt: renderedPrompt,
      docs: options.docs,
      output: {
        format: options.output?.format || this.output?.format || undefined,
        schema: options.output?.schema || this.output?.schema,
        jsonSchema: options.output?.jsonSchema || this.output?.jsonSchema,
      },
      tools: (options.tools || []).concat(this.tools || []),
      streamingCallback: options.streamingCallback,
      returnToolRequests: options.returnToolRequests,
      use: options.use,
    } as GenerateOptions<O, CustomOptions>;
  }

  /**
   * Renders the prompt template based on user input.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns a `GenerateOptions` object to be used with the `generate()` function from @genkit-ai/ai.
   */
  render<
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): GenerateOptions<CustomOptions, O> {
    return this._generateOptions(opt);
  }

  async renderInNewSpan<
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(opt: PromptGenerateOptions<I>): Promise<GenerateOptions<CustomOptions, O>> {
    const spanName = this.variant ? `${this.name}.${this.variant}` : this.name;
    return runInNewSpan(
      {
        metadata: {
          name: spanName,
          input: opt,
        },
        labels: {
          [SPAN_TYPE_ATTR]: 'dotprompt',
        },
      },
      async (metadata) => {
        setCustomMetadataAttribute('prompt_fingerprint', this.hash);
        const generateOptions = this._generateOptions<CustomOptions, O>(opt);
        metadata.output = generateOptions;
        return generateOptions;
      }
    );
  }

  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateResponse`.
   */
  async generate<
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    const renderedOpts = this.renderInNewSpan<CustomOptions, O>(opt);
    return generate<CustomOptions, O>(this.registry, renderedOpts);
  }

  /**
   * Generates a streaming response by rendering the prompt template with given user input and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  async generateStream<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny>(
    opt: PromptGenerateOptions<I, CustomOptions>
  ): Promise<GenerateStreamResponse> {
    const renderedOpts = await this.renderInNewSpan<CustomOptions>(opt);
    return generateStream(this.registry, renderedOpts);
  }
}

export class DotpromptRef<Variables = unknown> {
  name: string;
  variant?: string;
  dir?: string;
  private _prompt?: Dotprompt<Variables>;

  constructor(
    name: string,
    options?: {
      variant?: string;
      dir?: string;
    }
  ) {
    this.name = name;
    this.variant = options?.variant;
    this.dir = options?.dir;
  }

  /** Loads the prompt which is referenced. */
  async loadPrompt(registry: Registry): Promise<Dotprompt<Variables>> {
    if (this._prompt) return this._prompt;
    this._prompt = (await lookupPrompt(
      registry,
      this.name,
      this.variant,
      this.dir
    )) as Dotprompt<Variables>;
    return this._prompt;
  }

  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateResponse`.
   */

  async generate<
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    registry: Registry,
    opt: PromptGenerateOptions<Variables, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    const prompt = await this.loadPrompt(registry);
    return prompt.generate<CustomOptions, O>(opt);
  }

  /**
   * Renders the prompt template based on user input.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns a `GenerateOptions` object to be used with the `generate()` function from @genkit-ai/ai.
   */
  async render<
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    registry: Registry,

    opt: PromptGenerateOptions<Variables, CustomOptions>
  ): Promise<GenerateOptions<z.ZodTypeAny, O>> {
    const prompt = await this.loadPrompt(registry);
    return prompt.render<CustomOptions, O>(opt);
  }
}

/**
 * Define a dotprompt in code. This function is offered as an alternative to definitions in .prompt files.
 *
 * @param options the prompt definition, including its name, variant and model. Any options from .prompt file front matter are accepted.
 * @param template a string template, comparable to the main body of a prompt file.
 * @returns the newly defined prompt.
 */
export function defineDotprompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: PromptMetadata<I, CustomOptions>,
  template: string
): Dotprompt<z.infer<I>> {
  const prompt = new Dotprompt(registry, options, template);
  prompt.define({ description: options.description });
  return prompt;
}
