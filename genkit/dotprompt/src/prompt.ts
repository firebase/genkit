import { readFileSync } from 'fs';
import { PromptMetadata } from './metadata.js';
import { compile } from './template.js';
import { GenerationRequest, MessageData } from '@google-genkit/ai/model';
import fm from 'front-matter';
import { GenerationResponse, generate } from '@google-genkit/ai/generate';

export class PromptFile<Variables = unknown> {
  metadata: PromptMetadata;
  template: string;
  variants: Record<string, PromptFile>;

  private _render: (
    variables: Variables,
    options?: { context?: string[]; history?: MessageData[] }
  ) => MessageData[];

  static parse(source: string) {
    const fmResult = (fm as any)(source);
    return new PromptFile(fmResult.body, fmResult.attributes as PromptMetadata);
  }

  static loadFile(path: string) {
    return PromptFile.parse(readFileSync(path, 'utf8'));
  }

  constructor(
    template: string,
    metadata: PromptMetadata,
    options?: { variants?: Record<string, PromptFile> }
  ) {
    this.metadata = metadata;
    this.template = template;
    this.variants = options?.variants || {};
    this._render = compile(template, metadata);
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

  generate(
    variables: Variables,
    options?: { candidates?: number; variant?: string }
  ): Promise<GenerationResponse> {
    const { variant, ...opts } = options || {};
    if (variant && !this.variants[variant]) {
      throw new Error(`Variant '${variant}' not found.`);
    } else if (variant) {
      return this.variants[variant].generate(variables, opts);
    }

    const messages = this.renderMessages(variables);
    return generate({
      model: this.metadata.model,
      config: this.metadata.config || {},
      history: messages.slice(0, messages.length - 1),
      prompt: messages[messages.length - 1].content,
      candidates: options?.candidates || 1,
      output: {
        format: this.metadata.output?.format || undefined,
        jsonSchema: this.metadata.output?.schema,
      },
    });
  }
}
