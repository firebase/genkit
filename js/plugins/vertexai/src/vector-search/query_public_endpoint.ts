import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { findNeighborsResponseSchema } from './types';

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

export async function queryPublicEndpoint(
  params: QueryPublicEndpointParams
): Promise<z.infer<typeof findNeighborsResponseSchema>> {
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
    logger.error('Error querying index: ', response.statusText);
  }
  const body = await response.json();

  let parsedBody: z.infer<typeof findNeighborsResponseSchema>;

  try {
    parsedBody = findNeighborsResponseSchema.parse(body);
  } catch (error) {
    logger.error(
      'Could not parse findNeighbors response from Vertex AI: ',
      error
    );
    throw error;
  }

  return parsedBody;
}
