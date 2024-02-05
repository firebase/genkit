import { readFileSync } from 'fs';
import { PromptMetadata } from './metadata';
import { compile } from './template';
import { MessageData } from '@google-genkit/ai/model';
import fm from 'front-matter';
import { generate } from '@google-genkit/ai/generate';

export class PromptFile<Variables = unknown> {
  metadata: PromptMetadata;
  template: string;
  private _render: (
    variables: Variables,
    options?: { context?: string[]; history?: MessageData[] }
  ) => MessageData[];

  static parse(source: string) {
    const fmResult = fm(source);
    return new PromptFile(fmResult.body, fmResult.attributes as PromptMetadata);
  }

  static loadFile(path: string) {
    return PromptFile.parse(readFileSync(path, 'utf8'));
  }

  constructor(template: string, metadata: PromptMetadata) {
    this.metadata = metadata;
    this.template = template;
    this._render = compile(template, metadata);
  }

  render(variables: Variables) {
    return this._render(variables);
  }

  generate(variables: Variables, options?: { candidates?: number }) {
    const messages = this.render(variables);
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
