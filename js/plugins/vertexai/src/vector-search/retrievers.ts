import { embed } from '@genkit-ai/ai/embedder';

import {
  defineRetriever,
  RetrieverAction,
  retrieverRef,
} from '@genkit-ai/ai/retriever';

import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { queryPublicEndpoint } from './query_public_endpoint';
import { vertexVectorSearchOptions } from './types';
import { getProjectNumber } from './utils';

export function vertexRetrievers<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: vertexVectorSearchOptions<EmbedderCustomOptions>
) {
  const vectorSearchOptions = params.pluginOptions.vectorSearchIndexOptions;

  const defaultEmbedder = params.defaultEmbedder;

  // TODO remove ! after fixing the type
  const retrievers: RetrieverAction<z.ZodTypeAny>[] = [];
  for (const vectorSearchOption of vectorSearchOptions!) {
    const { documentRetriever, documentIdField, indexId, publicEndpoint } =
      vectorSearchOption;

    const embedder = vectorSearchOption.embedder ?? defaultEmbedder;
    const embedderOptions = vectorSearchOption.embedderOptions;

    const retriever = defineRetriever(
      {
        name: `vertexai/${indexId}`,
        configSchema: z.any(),
      },
      async (content, options) => {
        const queryEmbeddings = await embed({
          embedder,
          options: embedderOptions,
          content,
        });

        const accessToken = await params.authClient.getAccessToken();
        const projectId = params.pluginOptions.projectId!;
        const location = params.pluginOptions.location!;
        const publicEndpointDomainName = publicEndpoint;

        try {
          const queryResponse = await queryPublicEndpoint({
            featureVector: queryEmbeddings,
            neighborCount: options.k,
            accessToken: accessToken!,
            projectId,
            location,
            publicEndpointDomainName,
            projectNumber:
              params.pluginOptions.projectNumber ||
              (await getProjectNumber(projectId)),
            indexEndpointId: vectorSearchOption.indexEndpointId,
            deployedIndexId: indexId,
          });

          logger.info(queryResponse);

          const docIds = queryResponse.queries[0].neighbors.map((n) => {
            return n.datapoint.datapointId;
          });

          const documentResponse = await documentRetriever(docIds);

          logger.error(docIds);

          return {
            documents: [
              {
                content: [{ text: 'test' }],
              },
            ],
          };
        } catch (error) {
          console.error(error);
          return {
            documents: [],
          };
        }
      }
    );

    retrievers.push(retriever);
  }
  return retrievers;
}

export const vertexAiRetrieverRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return retrieverRef({
    name: `vertexai/${params.indexId}`,
    info: {
      label: params.displayName ?? `vertexAi - ${params.indexId}`,
    },
    configSchema: z.any().optional(),
  });
};
