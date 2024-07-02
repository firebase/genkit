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

import { embed } from '@genkit-ai/ai/embedder';
import {
  defineRetriever,
  RetrieverAction,
  retrieverRef,
} from '@genkit-ai/ai/retriever';
import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { queryPublicEndpoint } from './query_public_endpoint';
import { vertexVectorSearchOptions, VVSRetrieverOptionsSchema } from './types';
import { getProjectNumber } from './utils';

const DEFAULT_K = 10;

export function vertexRetrievers<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: vertexVectorSearchOptions<EmbedderCustomOptions>
) {
  const vectorSearchOptions = params.pluginOptions.vectorSearchIndexOptions;
  const defaultEmbedder = params.defaultEmbedder;

  const retrievers: RetrieverAction<z.ZodTypeAny>[] = [];

  for (const vectorSearchOption of vectorSearchOptions!) {
    const { documentRetriever, indexId, publicEndpoint } = vectorSearchOption;
    const embedder = vectorSearchOption.embedder ?? defaultEmbedder;
    const embedderOptions = vectorSearchOption.embedderOptions;

    const retriever = defineRetriever(
      {
        name: `vertexai/${indexId}`,
        configSchema: VVSRetrieverOptionsSchema,
      },
      async (content, options) => {
        const queryEmbeddings = await embed({
          embedder,
          options: embedderOptions,
          content,
        });
        logger.info(`Embeddings created successfully for index: ${indexId}`);

        const accessToken = await params.authClient.getAccessToken();

        if (!accessToken) {
          throw new Error(
            'Access token is required to define Vertex AI retriever'
          );
        }

        const projectId = params.pluginOptions.projectId;
        if (!projectId) {
          throw new Error(
            'Project ID is required to define Vertex AI retriever'
          );
        }
        const location = params.pluginOptions.location;
        if (!location) {
          throw new Error('Location is required to define Vertex AI retriever');
        }
        const publicEndpointDomainName = publicEndpoint;

        logger.info(
          `Defining Vertex AI Vector Search retriever, using project ID: ${projectId}, location: ${location}, endpoint: ${publicEndpointDomainName}`
        );

        try {
          let res = await queryPublicEndpoint({
            featureVector: queryEmbeddings,
            neighborCount: options?.k || DEFAULT_K,
            accessToken,
            projectId,
            location,
            publicEndpointDomainName,
            projectNumber:
              params.pluginOptions.projectNumber ||
              (await getProjectNumber(projectId)),
            indexEndpointId: vectorSearchOption.indexEndpointId,
            deployedIndexId: vectorSearchOption.deployedIndexId,
          });
          const nearestNeighbors = res.nearestNeighbors;

          const queryRes = nearestNeighbors ? nearestNeighbors[0] : null;
          const neighbors = queryRes ? queryRes.neighbors : null;
          if (!nearestNeighbors || !queryRes || !neighbors) {
            logger.warn('No nearest neighbors found in query response');
            return { documents: [] };
          }

          if (neighbors.some((n) => !n.datapoint || !n.datapoint.datapointId)) {
            logger.warn('Some neighbors do not have datapoints');
          }

          const documents = await documentRetriever(neighbors, options);

          logger.info(`Documents retrieved for index: ${indexId}`);
          return { documents };
        } catch (error) {
          handleRetrieverError(error, indexId);
        }
      }
    );

    retrievers.push(retriever);
  }

  return retrievers;
}

function handleRetrieverError(error: unknown, indexId: string): never {
  if (error instanceof Error) {
    logger.error(
      `Error in retriever process for index: ${indexId} - ${error.message}`
    );
    throw new Error(`Error: ${error}, ${error.message}`);
  } else {
    logger.error(
      `Unknown error in retriever process for index: ${indexId} - ${error}`
    );
    throw error;
  }
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
