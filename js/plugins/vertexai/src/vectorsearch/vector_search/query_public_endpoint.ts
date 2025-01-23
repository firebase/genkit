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

import { logger } from 'genkit/logging';
import { FindNeighborsResponse } from './types';

interface QueryPublicEndpointParams {
  featureVector: number[];
  neighborCount: number;
  accessToken: string;
  projectId: string;
  location: string;
  indexEndpointId: string;
  publicDomainName: string;
  projectNumber: string;
  deployedIndexId: string;
}
/**
 * Queries a public index endpoint to find neighbors for a given feature vector.
 *
 * This function sends a request to a specified public endpoint to find neighbors
 * for a given feature vector using the provided parameters.
 *
 * @param {QueryPublicEndpointParams} params - The parameters required to query the public endpoint.
 * @param {number[]} params.featureVector - The feature vector for which to find neighbors.
 * @param {number} params.neighborCount - The number of neighbors to retrieve.
 * @param {string} params.accessToken - The access token for authorization.
 * @param {string} params.projectId - The ID of the Google Cloud project.
 * @param {string} params.location - The location of the index endpoint.
 * @param {string} params.indexEndpointId - The ID of the index endpoint.
 * @param {string} params.publicDomainName - The domain name of the public endpoint.
 * @param {string} params.projectNumber - The project number.
 * @param {string} params.deployedIndexId - The ID of the deployed index.
 * @returns {Promise<FindNeighborsResponse>} - The response from the public endpoint.
 */
export async function queryPublicEndpoint(
  params: QueryPublicEndpointParams
): Promise<FindNeighborsResponse> {
  const {
    featureVector,
    neighborCount,
    accessToken,
    indexEndpointId,
    publicDomainName,
    projectNumber,
    deployedIndexId,
    location,
  } = params;
  const url = new URL(
    `https://${publicDomainName}/v1/projects/${projectNumber}/locations/${location}/indexEndpoints/${indexEndpointId}:findNeighbors`
  );

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
  return response.json() as FindNeighborsResponse;
}
