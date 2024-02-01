import { action, Action } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
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
  O extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
> = Action<I, O> & {
  __inputType: InputType;
  __customOptionsType: CustomOptions;
};

function withMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
>(
  embedder: Action<I, O>,
  inputType: InputType,
  customOptionsType: CustomOptions
): EmbedderAction<I, O, InputType, CustomOptions> {
  const withMeta = embedder as EmbedderAction<I, O, InputType, CustomOptions>;
  withMeta.__inputType = inputType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 * Creates embedder model for the provided {@link EmbedderFn} model implementation.
 */
export function embedderFactory<
  InputType extends z.ZodTypeAny,
  EmbedderOptions extends z.ZodTypeAny
>(
  provider: string,
  embedderId: string,
  inputType: InputType,
  customOptionsType: EmbedderOptions,
  fn: EmbedderFn<InputType, EmbedderOptions>
) {
  const embedder = action(
    {
      name: 'embed',
      input: z.object({
        input: inputType,
        options: customOptionsType.optional(),
      }),
      output: EmbeddingSchema,
    },
    (i) => fn(i.input, i.options)
  );
  registry.registerAction('embedder', `${provider}/${embedderId}`, embedder);
  return withMetadata(embedder, inputType, customOptionsType);
}

/**
 * A veneer for interacting with embedder models.
 */
export async function embed<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  InputType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
>(params: {
  embedder: EmbedderAction<I, O, InputType, CustomOptions>;
  input: z.infer<InputType>;
  options?: z.infer<CustomOptions>;
}): Promise<Embedding> {
  return await params.embedder({
    input: params.input,
    options: params.options,
  });
}
