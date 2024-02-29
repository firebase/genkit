import { action, Action } from '@google-genkit/common';
import { lookupAction } from '@google-genkit/common/registry';
import { setCustomMetadataAttributes } from '@google-genkit/common/tracing';
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
export function embedder<
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
  return withMetadata(embedder, options.inputType, options.customOptionsType);
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
    embedder = lookupAction(`/embedder/${params.embedder.name}`);
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
