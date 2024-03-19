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

import { ModelArgument } from '@genkit-ai/ai/model';
import { GenerationConfigSchema, GenerationConfig } from '@genkit-ai/ai/model';
import { ToolArgument } from '@genkit-ai/ai/tool';
import z from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

// TODO: Do a real type here.
type JSONSchema = unknown;

/**
 * Metadata for a prompt.
 */
export interface PromptMetadata<Options extends z.ZodTypeAny = z.ZodTypeAny> {
  /** The name of the prompt. */
  name: string;
  /** The variant name for the prompt. */
  variant?: string;

  /**
   * The name of the model to use for this prompt, e.g. `google-vertex/gemini-pro`
   * or `openai/gpt-4-0125-preview`.
   */
  model: ModelArgument<Options>;

  /** Names of tools (registered separately) to allow use of in this prompt. */
  tools?: ToolArgument[];

  /** Model configuration. Not all models support all options. */
  config?: GenerationConfig<z.infer<Options>>;

  input?: {
    /** Defines the default input variable values to use if none are provided. */
    default?: any;
    /** Zod schema defining the input variables. */
    schema?: z.ZodTypeAny;
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
  model: z.string(),
  tools: z.array(z.string()).optional(),
  config: GenerationConfigSchema.optional(),
  input: z
    .object({
      schema: z.unknown(),
      default: z.any(),
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

function stripUndefined(obj: any) {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  for (const key in obj) {
    if (obj[key] === undefined) {
      delete obj[key];
    } else if (typeof obj[key] === 'object') {
      stripUndefined(obj[key]); // Recurse into nested objects
    }
  }
  return obj;
}

export function toMetadata(attributes: unknown): Partial<PromptMetadata> {
  const fm = PromptFrontmatterSchema.parse(attributes);
  return stripUndefined({
    name: fm.name,
    model: fm.model,
    config: fm.config,
    input: fm.input
      ? { default: fm.input.default, jsonSchema: fm.input.schema }
      : undefined,
    output: fm.output
      ? { format: fm.output.format, jsonSchema: fm.output.schema }
      : undefined,
    metadata: fm.metadata,
    tools: fm.tools,
  });
}

export function toFrontmatter(md: PromptMetadata): PromptFrontmatter {
  return stripUndefined({
    name: md.name,
    model: typeof md.model === 'string' ? md.model : md.model.name,
    config: md.config,
    input: md.input
      ? {
          default: md.input.default,
          schema: md.input.schema
            ? zodToJsonSchema(md.input.schema)
            : md.input.jsonSchema,
        }
      : undefined,
    output: md.output
      ? {
          format: md.output.format,
          schema: md.output.schema
            ? zodToJsonSchema(md.output.schema)
            : md.output.jsonSchema,
        }
      : undefined,
    metadata: md.metadata,
    tools: md.tools?.map((t) => (typeof t === 'string' ? t : t.__action.name)),
  });
}
