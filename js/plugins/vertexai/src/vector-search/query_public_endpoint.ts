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

import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { FindNeighborsResponseSchema } from './types';

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
): Promise<z.infer<typeof FindNeighborsResponseSchema>> {
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
  return response.json();
}
