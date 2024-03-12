import { setCustomMetadataAttribute } from '@genkit-ai/common/tracing';
import { z } from 'zod';
import * as crypto from 'crypto';
import * as fs from 'fs';
import fm from 'front-matter';
import { ModelId, ModelIdSchema } from './types';
import { action } from '@genkit-ai/common';

function metadataPrefix(name: string) {
  return `ai:${name}`;
}

export const PromptMetadataSchema = z.object({
  name: z.string().readonly().optional(),
  fileName: z.string().readonly().optional(),
  modelId: ModelIdSchema.readonly().optional(),
  hash: z.string().readonly().optional(),
  copied: z.boolean().optional(),
});

export const TextPartSchema = z.string();
export const InlineDataPartSchema = z.object({
  uri: z.string(),
  mimeType: z.string(),
});

export const PartSchema = TextPartSchema.or(InlineDataPartSchema);

export const PromptSchema = z.object({
  prompt: z.string(),
  attributes: z.record(z.string(), z.any()).optional(),
  metadata: PromptMetadataSchema.optional(),
});

export const MultimodalPromptSchema = z.object({
  prompt: z.array(PartSchema),
  attributes: z.record(z.string(), z.any()).optional(),
  metadata: PromptMetadataSchema.optional(),
});

export type Prompt = z.infer<typeof PromptSchema>;
export type MultimodalPrompt = z.infer<typeof MultimodalPromptSchema>;

/**
 * Normalizes string or prompt input into a {@link Prompt} object.
 * If `copy` is true then makes a copy (clones) the prompt.
 */
export function prompt(
  input: string | Prompt,
  attributes?: Record<string, any>,
  metadata?: z.infer<typeof PromptMetadataSchema>,
  copy?: boolean
): Prompt {
  if (typeof input === 'string') {
    return { prompt: input, attributes, metadata };
  }
  if (copy) {
    return {
      prompt: input.prompt,
      attributes: input.attributes,
      metadata: { ...input.metadata, copied: true },
    };
  } else {
    return input;
  }
}

const promptTemplateAction = action(
  {
    name: 'promptTemplate',
    input: z.object({
      template: z.string().or(PromptSchema),
      variables: z.record(z.string(), z.any()),
    }),
    output: PromptSchema,
  },
  async (input) => {
    const newPrompt = prompt(input.template, undefined, undefined, true);
    const matches = [...newPrompt.prompt.matchAll(/{(.+?)}/g)];
    for (const m of matches) {
      try {
        newPrompt.prompt = newPrompt.prompt.replace(
          m[0],
          fillTemplate(m[1], input.variables)
        );
      } catch (e) {
        console.log(`promptTemplate: failed to substitute ${m[0]}:\n${e}`);
      }
    }
    setCustomMetadataAttribute(metadataPrefix('type'), 'promptTemplate');
    return newPrompt;
  }
);

/**
 * Substitutes variables in the provided prompt template.
 */
export async function promptTemplate(input: {
  template: string | Prompt;
  variables: Record<string, any>;
}): Promise<Prompt> {
  return await promptTemplateAction(input);
}

const fillTemplate = function (templateString, templateVars) {
  // TODO: super unsafe!
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  return new Function(`return this.${templateString};`).call(templateVars);
};

/**
 * Loads prompt from a file.
 */
export function loadPrompt(id: string): z.infer<typeof PromptSchema> {
  const fileContents = fs.readFileSync(id, { encoding: 'utf8', flag: 'r' });
  const parsedPrompt = fm<Record<string, any>>(fileContents);
  return {
    prompt: parsedPrompt.body,
    attributes: parsedPrompt.attributes,
    metadata: {
      fileName: id,
      hash: crypto
        .createHash('md5')
        .update(JSON.stringify(fileContents))
        .digest('hex'),
      modelId: getModelIdMaybe(parsedPrompt.attributes),
    },
  };
}

function getModelIdMaybe(attrs: Record<string, any>): ModelId | undefined {
  if (!attrs || !attrs.modelName || !attrs.modelProvider) return undefined;
  return {
    modelName: attrs.modelName,
    modelProvider: attrs.modelProvider,
  };
}
