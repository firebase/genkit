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

import { action, Action } from '@genkit-ai/common';
import * as registry from '@genkit-ai/common/registry';
import { lookupAction } from '@genkit-ai/common/registry';
import { setCustomMetadataAttributes } from '@genkit-ai/common/tracing';
import * as z from 'zod';

export const EmbeddingSchema = z.array(z.number());
type Embedding = z.infer<typeof EmbeddingSchema>;

type EmbedderFn<
  InputType extends z.ZodTypeAny,
  EmbedderOptions extends z.ZodTypeAny
> = (
  input: z.infer<InputType>,
  embedderOpts?: z.infer<EmbedderOptions>
) => Promise<Embedding>;

export type EmbedderAction<
  I extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
> = Action<I, typeof EmbeddingSchema> & {
  __inputType: InputType;
  __customOptionsType: CustomOptions;
  getDimension: () => number;
};

function withMetadata<
  I extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
>(
  embedder: Action<I, typeof EmbeddingSchema>,
  inputType: InputType,
  customOptionsType: CustomOptions
): EmbedderAction<I, InputType, CustomOptions> {
  const withMeta = embedder as EmbedderAction<I, InputType, CustomOptions>;
  withMeta.__inputType = inputType;
  withMeta.__customOptionsType = customOptionsType;
  withMeta.getDimension = () => embedder.__action.metadata?.dimension as number;
  return withMeta;
}

/**
 * Creates embedder model for the provided {@link EmbedderFn} model implementation.
 */
export function defineEmbedder<
  InputType extends z.ZodTypeAny,
  EmbedderOptions extends z.ZodTypeAny
>(
  options: {
    provider: string;
    embedderId: string;
    inputType: InputType;
    info: EmbedderInfo;
    customOptionsType: EmbedderOptions;
  },
  runner: EmbedderFn<InputType, EmbedderOptions>
) {
  const embedder = action(
    {
      name: options.embedderId,
      input: z.object({
        input: options.inputType,
        options: options.customOptionsType.optional(),
      }),
      output: EmbeddingSchema,
      metadata: {
        info: options.info,
      },
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'embedder' });
      return runner(i.input, i.options);
    }
  );
  const ewm = withMetadata(
    embedder,
    options.inputType,
    options.customOptionsType
  );
  registry.registerAction('embedder', ewm.__action.name, ewm);
  return ewm;
}

/**
 * A veneer for interacting with embedder models.
 */
export async function embed<
  I extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  EmbedderOptions extends z.ZodTypeAny
>(params: {
  embedder:
    | EmbedderAction<I, InputType, EmbedderOptions>
    | EmbedderReference<EmbedderOptions>;
  input: z.infer<InputType>;
  options?: z.infer<EmbedderOptions>;
}): Promise<Embedding> {
  let embedder: EmbedderAction<I, InputType, EmbedderOptions>;
  if (Object.hasOwnProperty.call(params.embedder, 'info')) {
    embedder = await lookupAction(`/embedder/${params.embedder.name}`);
  } else {
    embedder = params.embedder as EmbedderAction<I, InputType, EmbedderOptions>;
  }
  if (!embedder) {
    throw new Error('Unable to utilze the provided embedder');
  }
  return await embedder({
    input: params.input,
    options: params.options,
  });
}

export const EmbedderInfoSchema = z.object({
  /** Acceptable names for this embedder (e.g. different versions). */
  names: z.array(z.string()).optional(),
  /** Friendly label for this model (e.g. "Google AI - Gemini Pro") */
  label: z.string().optional(),
  /** Supported model capabilities. */
  supports: z
    .object({
      /** Model can input this type of data. */
      input: z.array(z.enum(['text', 'image'])).optional(),
      /** Model can support multiple languages */
      multilingual: z.boolean().optional(),
    })
    .optional(),
  /** Embedding dimension */
  dimension: z.number().optional(),
});
export type EmbedderInfo = z.infer<typeof EmbedderInfoSchema>;

export interface EmbedderReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: EmbedderInfo;
}

/**
 * Helper method to configure a {@link EmbedderReference} to a plugin.
 */
export function embedderRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: EmbedderReference<CustomOptionsSchema>
): EmbedderReference<CustomOptionsSchema> {
  return { ...options };
}
