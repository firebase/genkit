import { embed, EmbedderArgument, embedMany } from '@genkit-ai/ai/embedder';
import { google } from 'googleapis';

import {
  CommonRetrieverOptionsSchema,
  defineIndexer,
  defineRetriever,
  indexerRef,
  retrieverRef,
} from '@genkit-ai/ai/retriever';
import * as aiplatform from '@google-cloud/aiplatform';

import { logger } from '@genkit-ai/core/logging';
import { GoogleAuth } from 'google-auth-library';
import z from 'zod';
import { PluginOptions } from '.';

type IIndexDatapoint =
  aiplatform.protos.google.cloud.aiplatform.v1.IIndexDatapoint;

class Datapoint extends aiplatform.protos.google.cloud.aiplatform.v1
  .IndexDatapoint {
  constructor(properties: IIndexDatapoint) {
    super(properties);
  }
}

interface VVSOptions<EmbedderCustomOptions extends z.ZodTypeAny> {
  pluginOptions: PluginOptions;
  authClient: GoogleAuth;
  embedder: EmbedderArgument<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}

const VVSOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().max(1000),
});
export function configureVVSIndexer<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: VVSOptions<EmbedderCustomOptions>
) {
  const { documentIndexer, documentIdField } =
    params.pluginOptions.vectorSearchOptions!;
  const { embedder, embedderOptions } = params;
  const indexId = params.pluginOptions.vectorSearchOptions!.indexId;

  return defineIndexer(
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
}

async function upsertDatapoints(params: {
  datapoints: IIndexDatapoint[];
  authClient: GoogleAuth;
  projectId: string;
  location: string;
  indexId: string;
}) {
  const { datapoints, authClient, projectId, location, indexId } = params;
  const accessToken = await getAccessToken(authClient);
  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/indexes/${indexId}:upsertDatapoints`;

  const requestBody = {
    datapoints: datapoints.map((dp) => ({
      datapoint_id: dp.datapointId,
      feature_vector: dp.featureVector,
    })),
  };

  logger.info(requestBody);

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });

  logger.info(response);

  if (!response.ok) {
    logger.error(response);
    throw new Error(`Error: ${JSON.stringify(response.body, null, 2)}`);
  }

  return await response.json();
}

export function configureVVSRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(params: VVSOptions<EmbedderCustomOptions>) {
  const { documentRetriever, documentIdField } =
    params.pluginOptions.vectorSearchOptions!;
  const indexId = params.pluginOptions.vectorSearchOptions!.indexId;
  return defineRetriever(
    {
      name: `vertexai/${indexId}`,
      configSchema: VVSOptionsSchema,
    },
    async (content, options) => {
      const queryEmbeddings = await embed({
        embedder: params.embedder,
        content,
        options: params.embedderOptions,
      });

      const accessToken = await params.authClient.getAccessToken();
      const projectId = params.pluginOptions.projectId!;
      const location = params.pluginOptions.location!;
      const publicEndpointDomainName =
        params.pluginOptions.vectorSearchOptions!.publicEndpoint;

      try {
        const queryResponse = await queryPublicEndpoint({
          featureVector: queryEmbeddings,
          neighborCount: options.k,
          accessToken: accessToken!,
          projectId,
          location,
          publicEndpointDomainName,
          projectNumber:
            params.pluginOptions.vectorSearchOptions!.projectNumber!,
          indexEndpointId:
            params.pluginOptions.vectorSearchOptions!.indexEndpointId!,
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
}

export async function getAccessToken(auth: GoogleAuth) {
  const client = await auth.getClient();
  const _accessToken = await client.getAccessToken();
  return _accessToken.token;
}

export async function getProjectNumber(
  projectId: string
): Promise<string | null> {
  const authClient = await google.auth.getClient({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });

  const client = google.cloudresourcemanager('v1');

  try {
    const response = await client.projects.get({
      projectId: projectId,
      auth: authClient,
    });
    return response.data.projectNumber || null;
  } catch (error) {
    console.error('Error fetching project number:', error);
    return null;
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
    configSchema: VVSOptionsSchema.optional(),
  });
};

export const vertexAiIndexerRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return indexerRef({
    name: `vertexai/${params.indexId}`,
    info: {
      label: params.displayName ?? `vertexAi - ${params.indexId}`,
    },
    configSchema: VVSOptionsSchema.optional(),
  });
};

interface QueryPublicEndpointParams {
  featureVector: number[];
  neighborCount: number;
  accessToken: string;
  projectId: string;
  location: string;
  indexEndpointId: string;
  publicEndpointDomainName: string;
  projectNumber: string;
  deployedIndexId: string;
}

async function queryPublicEndpoint(
  params: QueryPublicEndpointParams
): Promise<any> {
  const {
    featureVector,
    neighborCount,
    accessToken,
    indexEndpointId,
    publicEndpointDomainName,
    projectNumber,
    deployedIndexId,
    location,
  } = params;
  const url = `${publicEndpointDomainName}/v1/projects/${projectNumber}/locations/${location}/indexEndpoints/${indexEndpointId}:findNeighbors`;

  const requestBody = {
    deployed_index_id: deployedIndexId,
    queries: [
      {
        datapoint: {
          datapoint_id: '0',
          feature_vector: featureVector,
        },
        neighbor_count: neighborCount,
      },
    ],
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error(`Error: ${response.statusText}`);
  }

  logger.info(response);

  return await response.json();
}
