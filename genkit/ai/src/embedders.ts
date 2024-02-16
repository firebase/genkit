import { action, Action } from '@google-genkit/common';
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
export function embedderFactory<
  InputType extends z.ZodTypeAny,
  EmbedderOptions extends z.ZodTypeAny
>(
  options: {
    provider: string;
    embedderId: string;
    dimension: number;
    inputType: InputType;
    customOptionsType: EmbedderOptions;
  },
  runner: EmbedderFn<InputType, EmbedderOptions>
) {
  const embedder = action(
    {
      name: 'embed',
      input: z.object({
        input: options.inputType,
        options: options.customOptionsType.optional(),
      }),
      output: EmbeddingSchema,
      metadata: {
        dimension: options.dimension,
      },
    },
    (i) => runner(i.input, i.options)
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
  embedder: EmbedderAction<I, InputType, EmbedderOptions>;
  input: z.infer<InputType>;
  options?: z.infer<EmbedderOptions>;
}): Promise<Embedding> {
  return await params.embedder({
    input: params.input,
    options: params.options,
  });
}
