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

export const MultipartDocumentSchema = BaseDocumentSchema.extend({
  content: z.object({
    mimeType: z.string(),
    data: z.string(),
    blob: z.instanceof(Blob).optional(),
  }),
});
export type MultipartDocument = z.infer<typeof MultipartDocumentSchema>;

type DocumentSchemaType =
  | typeof TextDocumentSchema
  | typeof MultipartDocumentSchema;

type RetrieverFn<
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny
> = (
  query: z.infer<QueryType>,
  queryOpts: z.infer<RetrieverOptions>
) => Promise<Array<z.infer<DocType>>>;

type IndexerFn<
  DocType extends DocumentSchemaType,
  IndexerOptions extends z.ZodTypeAny
> = (
  docs: Array<z.infer<DocType>>,
  indexerOpts: z.infer<IndexerOptions>
) => Promise<void>;

type DocumentsCollectionType<DocType extends DocumentSchemaType> =
  z.ZodArray<DocType>;

export type RetrieverAction<
  I extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny
> = Action<I, DocumentsCollectionType<DocType>> & {
  __queryType: QueryType;
  __docType: DocType;
  __customOptionsType: RetrieverOptions;
};

export type IndexerAction<
  I extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  IndexerOptions extends z.ZodTypeAny
> = Action<I, z.ZodVoid> & {
  __docType: DocType;
  __customOptionsType: IndexerOptions;
};

/**
 * Encapsulation of both {@link RetrieverAction} and {@link IndexerAction}.
 */
export interface DocumentStore<
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny,
  IndexerOptions extends z.ZodTypeAny
> {
  (params: {
    query: z.infer<QueryType>;
    options: z.infer<RetrieverOptions>;
  }): Promise<Array<z.infer<DocType>>>;
  index: (params: {
    docs: Array<z.infer<DocType>>;
    options: z.infer<IndexerOptions>;
  }) => Promise<void>;
}

function retrieverWithMetadata<
  I extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny
>(
  retriever: Action<I, DocumentsCollectionType<DocType>>,
  queryType: QueryType,
  docType: DocType,
  customOptionsType: RetrieverOptions
): RetrieverAction<I, QueryType, DocType, RetrieverOptions> {
  const withMeta = retriever as RetrieverAction<
    I,
    QueryType,
    DocType,
    RetrieverOptions
  >;
  withMeta.__queryType = queryType;
  withMeta.__docType = docType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

function indexerWithMetadata<
  I extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  IndexerOptions extends z.ZodTypeAny
>(
  indexer: Action<I, z.ZodVoid>,
  docType: DocType,
  customOptionsType: IndexerOptions
): IndexerAction<I, DocType, IndexerOptions> {
  const withMeta = indexer as IndexerAction<I, DocType, IndexerOptions>;
  withMeta.__docType = docType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 *  Creates a retriever action for the provided {@link RetrieverFn} implementation.
 */
export function retrieverFactory<
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny
>(
  options: {
    provider: string;
    retrieverId: string;
    queryType: QueryType;
    documentType: DocType;
    customOptionsType: RetrieverOptions;
  },
  runner: RetrieverFn<QueryType, DocType, RetrieverOptions>
) {
  const retriever = action(
    {
      name: 'retrieve',
      input: z.object({
        query: options.queryType,
        options: options.customOptionsType,
      }),
      output: z.array<DocumentSchemaType>(options.documentType),
    },
    (i) => runner(i.query, i.options)
  );
  registry.registerAction(
    'retriever',
    `${options.provider}/${options.retrieverId}`,
    retriever
  );
  return retrieverWithMetadata(
    retriever,
    options.queryType,
    options.documentType,
    options.customOptionsType
  );
}

/**
 *  Creates an indexer action for the provided {@link IndexerFn} implementation.
 */
export function indexerFactory<
  DocType extends DocumentSchemaType,
  IndexerOptions extends z.ZodTypeAny
>(
  options: {
    provider: string;
    indexerId: string;
    documentType: DocType;
    customOptionsType: IndexerOptions;
  },
  runner: IndexerFn<DocType, IndexerOptions>
) {
  const indexer = action(
    {
      name: 'index',
      input: z.object({
        docs: z.array(options.documentType),
        options: options.customOptionsType,
      }),
      output: z.void(),
    },
    (i) => runner(i.docs, i.options)
  );
  registry.registerAction(
    'indexer',
    `${options.provider}/${options.indexerId}`,
    indexer
  );
  return indexerWithMetadata(
    indexer,
    options.documentType,
    options.customOptionsType
  );
}

/**
 * Creates a {@link DocumentStore} based on provided {@link RetrieverFn} and {@link IndexerFn}.
 */
export function documentStoreFactory<
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny,
  IndexerOptions extends z.ZodTypeAny
>(params: {
  provider: string;
  id: string;
  queryType: QueryType;
  documentType: DocType;
  retrieverOptionsType: RetrieverOptions;
  indexerOptionsType: IndexerOptions;
  retrieveFn: RetrieverFn<QueryType, DocType, RetrieverOptions>;
  indexFn: IndexerFn<DocType, IndexerOptions>;
}) {
  const {
    provider,
    id,
    queryType,
    documentType,
    retrieverOptionsType,
    indexerOptionsType,
  } = { ...params };
  const indexer = indexerFactory(
    {
      provider,
      indexerId: id,
      documentType,
      customOptionsType: indexerOptionsType,
    },
    params.indexFn
  );
  const retriever = retrieverFactory(
    {
      provider,
      retrieverId: id,
      queryType,
      documentType,
      customOptionsType: retrieverOptionsType,
    },
    params.retrieveFn
  );

  const store = ((params: {
    query: z.infer<QueryType>;
    options: z.infer<RetrieverOptions>;
  }) =>
    retriever({
      query: params.query,
      options: params.options,
    })) as DocumentStore<QueryType, DocType, RetrieverOptions, IndexerOptions>;
  store.index = (params: {
    docs: Array<z.infer<typeof documentType>>;
    options: z.infer<IndexerOptions>;
  }) => indexer({ docs: params.docs, options: params.options });
  return store;
}

/**
 * Retrieves documents from a {@link RetrieverAction} or {@link DocumentStore}
 * based on the provided query.
 */
export async function retrieve<
  I extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny,
  IndexerOptions extends z.ZodTypeAny
>(params: {
  retriever:
    | DocumentStore<QueryType, DocType, RetrieverOptions, IndexerOptions>
    | RetrieverAction<I, QueryType, DocType, RetrieverOptions>;
  query: z.infer<QueryType>;
  options?: z.infer<RetrieverOptions>;
}): Promise<Array<z.infer<DocType>>> {
  return await params.retriever({
    query: params.query,
    options: params.options,
  });
}

/**
 * Indexes documents using a {@link IndexerAction} or a {@link DocumentStore}.
 */
export async function index<
  I extends z.ZodTypeAny,
  QueryType extends z.ZodTypeAny,
  DocType extends DocumentSchemaType,
  RetrieverOptions extends z.ZodTypeAny,
  IndexerOptions extends z.ZodTypeAny
>(params: {
  indexer:
    | DocumentStore<QueryType, DocType, RetrieverOptions, IndexerOptions>
    | IndexerAction<I, DocType, IndexerOptions>;
  docs: Array<z.infer<DocType>>;
  options?: z.infer<IndexerOptions>;
}): Promise<void> {
  if (
    'index' in params.indexer &&
    typeof params.indexer['index'] === 'function'
  ) {
    return await params.indexer.index({
      docs: params.docs,
      options: params.options,
    });
  }
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
  return await (params.indexer as IndexerAction<I, DocType, IndexerOptions>)({
    docs: params.docs,
    options: params.options,
  });
}

export const CommonRetrieverOptionsSchema = z.object({
  k: z.number().describe('Number of documents to retrieve').optional(),
});
