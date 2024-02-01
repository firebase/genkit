import { action, Action } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
import * as z from 'zod';

const BaseDocumentSchema = z.object({
  metadata: z.record(z.string(), z.any()).optional(),
});

export const TextDocumentSchema = BaseDocumentSchema.extend({
  content: z.string(),
});
export type TextDocument = z.infer<typeof TextDocumentSchema>;

export const MulipartDocumentSchema = BaseDocumentSchema.extend({
  content: z.object({
    mimeType: z.string(),
    data: z.string(),
    blob: z.instanceof(Blob).optional(),
  }),
});

type DocumentSchemaType =
  | typeof TextDocumentSchema
  | typeof MulipartDocumentSchema;
type Document = z.infer<DocumentSchemaType>;

type RetrieverFn<
  InputType extends z.ZodTypeAny,
  RetrieverOptions extends z.ZodTypeAny
> = (
  input: z.infer<InputType>,
  queryOpts: z.infer<RetrieverOptions>
) => Promise<Array<Document>>;

export type RetrieverAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
> = Action<I, O> & {
  __queryType: QueryType;
  __docType: DocType;
  __customOptionsType: CustomOptions;
};

function withMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
>(
  retriever: Action<I, O>,
  queryType: QueryType,
  docType: DocType,
  customOptionsType: CustomOptions
): RetrieverAction<I, O, QueryType, DocType, CustomOptions> {
  const withMeta = retriever as RetrieverAction<
    I,
    O,
    QueryType,
    DocType,
    CustomOptions
  >;
  withMeta.__queryType = queryType;
  withMeta.__docType = docType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 * Creates a reriever actopm for the provided {@link RetrieverFn} implementation.
 */
export function retrieverFactory<
  InputType extends z.ZodTypeAny,
  RetrieverOptions extends z.ZodTypeAny
>(
  provider: string,
  retrieverId: string,
  inputType: InputType,
  documentType: DocumentSchemaType,
  customOptionsType: RetrieverOptions,
  fn: RetrieverFn<InputType, RetrieverOptions>
) {
  const retriever = action(
    {
      name: 'retrieve',
      input: z.object({
        query: inputType,
        options: customOptionsType,
      }),
      output: z.array(documentType),
    },
    (i) => fn(i.query, i.options)
  );
  registry.registerAction('retriever', `${provider}/${retrieverId}`, retriever);
  return withMetadata(retriever, inputType, documentType, customOptionsType);
}

/**
 *
 */
export async function retrieve<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny
>(params: {
  dataStore: RetrieverAction<I, O, QueryType, DocType, CustomOptions>;
  query: z.infer<QueryType>;
  options?: z.infer<CustomOptions>;
}): Promise<Array<z.infer<DocType>>> {
  return await params.dataStore({
    query: params.query,
    options: params.options,
  });
}

export const CommonRetrieverOptionsSchema = z.object({
  k: z.number().describe('Number of documents to retrieve').optional(),
});
