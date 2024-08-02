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

//
// IMPORTANT: Please keep type definitions in sync with
//   genkit-tools/src/types/prompt.ts
//

import {
  GenerationCommonConfigSchema,
  ModelArgument,
} from '@genkit-ai/ai/model';
import { ToolArgument } from '@genkit-ai/ai/tool';
import { lookupSchema } from '@genkit-ai/core/registry';
import { JSONSchema, parseSchema, toJsonSchema } from '@genkit-ai/core/schema';
import z from 'zod';
import { picoschema } from './picoschema.js';

/**
 * Metadata for a prompt.
 */
export interface PromptMetadata<
  Input extends z.ZodTypeAny = z.ZodTypeAny,
  Options extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /** The name of the prompt. */
  name?: string;

  /** The variant name for the prompt. */
  variant?: string;

  /** The name of the model to use for this prompt, e.g. `vertexai/gemini-1.0-pro` */
  model?: ModelArgument<Options>;

  /** Names of tools (registered separately) to allow use of in this prompt. */
  tools?: ToolArgument[];

  /** Number of candidates to generate by default. */
  candidates?: number;

  /** Model configuration. Not all models support all options. */
  config?: z.infer<Options>;

  input?: {
    /** Defines the default input variable values to use if none are provided. */
    default?: any;
    /** Zod schema defining the input variables. */
    schema?: Input;
    /**
     * Defines the input variables that can be passed into the template in JSON schema form.
     * If not supplied, any object will be accepted. `{type: "object"}` is defaulted if not
     * supplied.
     */
    jsonSchema?: JSONSchema;
  };

  /** Defines the expected model output format. */
  output?: {
    /** Desired output format for this prompt. */
    format?: 'json' | 'text' | 'media';
    /** Zod schema defining the output structure (cannot be specified with non-json format). */
    schema?: z.ZodTypeAny;
    /** JSON schema of desired output (cannot be specified with non-json format). */
    jsonSchema?: JSONSchema;
  };

  /** Arbitrary metadata to be used by code, tools, and libraries. */
  metadata?: Record<string, any>;
}

/**
 * Formal schema for prompt YAML frontmatter.
 */
export const PromptFrontmatterSchema = z.object({
  name: z.string().optional(),
  variant: z.string().optional(),
  model: z.string().optional(),
  tools: z.array(z.string()).optional(),
  candidates: z.number().optional(),
  config: GenerationCommonConfigSchema.passthrough().optional(),
  input: z
    .object({
      default: z.any(),
      schema: z.unknown(),
    })
    .optional(),
  output: z
    .object({
      format: z.enum(['json', 'text', 'media']).optional(),
      schema: z.unknown().optional(),
    })
    .optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type PromptFrontmatter = z.infer<typeof PromptFrontmatterSchema>;

function stripUndefinedOrNull(obj: any) {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  for (const key in obj) {
    if (obj[key] === undefined || obj[key] === null) {
      delete obj[key];
    } else if (typeof obj[key] === 'object') {
      stripUndefinedOrNull(obj[key]); // Recurse into nested objects
    }
  }
  return obj;
}

function fmSchemaToSchema(fmSchema: any) {
  if (!fmSchema) return {};
  if (typeof fmSchema === 'string') return lookupSchema(fmSchema);
  return { jsonSchema: picoschema(fmSchema) };
}

export function toMetadata(attributes: unknown): Partial<PromptMetadata> {
  const fm = parseSchema<z.infer<typeof PromptFrontmatterSchema>>(attributes, {
    schema: PromptFrontmatterSchema,
  });

  let input: PromptMetadata['input'] | undefined;
  if (fm.input) {
    input = { default: fm.input.default, ...fmSchemaToSchema(fm.input.schema) };
  }

  let output: PromptMetadata['output'] | undefined;
  if (fm.output) {
    output = {
      format: fm.output.format,
      ...fmSchemaToSchema(fm.output.schema),
    };
  }

  return stripUndefinedOrNull({
    name: fm.name,
    variant: fm.variant,
    model: fm.model,
    config: fm.config,
    input,
    output,
    metadata: fm.metadata,
    tools: fm.tools,
    candidates: fm.candidates,
  });
}

export function toFrontmatter(md: PromptMetadata): PromptFrontmatter {
  return stripUndefinedOrNull({
    name: md.name,
    variant: md.variant,
    model: typeof md.model === 'string' ? md.model : md.model?.name,
    config: md.config,
    input: md.input
      ? {
          default: md.input.default,
          schema: toJsonSchema({
            schema: md.input.schema,
            jsonSchema: md.input.jsonSchema,
          }),
        }
      : undefined,
    output: md.output
      ? {
          format: md.output.format,
          schema: toJsonSchema({
            schema: md.output.schema,
            jsonSchema: md.output.jsonSchema,
          }),
        }
      : undefined,
    metadata: md.metadata,
    tools: md.tools?.map((t) =>
      typeof t === 'string' ? t : (t as any).__action?.name || (t as any).name
    ),
    candidates: md.candidates,
  });
}
