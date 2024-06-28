import { embedMany } from '@genkit-ai/ai/embedder';

import {
  defineIndexer,
  IndexerAction,
  indexerRef,
} from '@genkit-ai/ai/retriever';

import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { Datapoint, vertexVectorSearchOptions } from './types';
import { upsertDatapoints } from './upsert_datapoints';

export const vertexAiIndexerRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return indexerRef({
    name: `vertexai/${params.indexId}`,
    info: {
      label: params.displayName ?? `vertexAi - ${params.indexId}`,
    },
    configSchema: z.any().optional(),
  });
};

export function vertexIndexers<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: vertexVectorSearchOptions<EmbedderCustomOptions>
) {
  const vectorSearchOptions = params.pluginOptions.vectorSearchIndexOptions!;

  const defaultEmbedder = params.defaultEmbedder;

  // TODO remove ! after fixing the type, fix ZodTypeAny
  const indexers: IndexerAction<z.ZodTypeAny>[] = [];
  for (const vectorSearchOption of vectorSearchOptions!) {
    const { documentIndexer, documentIdField, indexId } = vectorSearchOption;
    const embedder = vectorSearchOption.embedder ?? defaultEmbedder;
    const embedderOptions = vectorSearchOption.embedderOptions;

    const indexer = defineIndexer(
      {
        name: `vertexai/${indexId}`,
        configSchema: z.any(),
      },
      async (docs, options) => {
        const ids = docs.map((doc) => doc.metadata![documentIdField!]);

        const embeddings = await embedMany({
          embedder,
          content: docs,
          options: embedderOptions,
        });

        const datapoints = embeddings.map(
          ({ embedding }, i) =>
            new Datapoint({
              datapointId: ids[i],
              featureVector: embedding,
            })
        );

        try {
          logger.info(`Attempting to upsert ${datapoints.length} datapoints`);
          logger.info(`Project ID: ${params.pluginOptions.projectId}`);
          logger.info(`Location: ${params.pluginOptions.location}`);
          logger.info(`Index ID: ${indexId}`);

          await upsertDatapoints({
            datapoints,
            authClient: params.authClient,
            projectId: params.pluginOptions.projectId!,
            location: params.pluginOptions.location!,
            indexId: indexId,
          });

          logger.info('Successfully indexed documents');
          await documentIndexer(docs);
        } catch (error) {
          logger.error(`Error during upsert: ${error}`);
          throw new Error(`Error: ${error}`);
        }
      }
    );

    indexers.push(indexer);
  }
  return indexers;
}
