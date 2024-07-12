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
import { GoogleAuth } from 'google-auth-library';
import { IIndexDatapoint } from './types';

interface UpsertDatapointsParams {
  datapoints: IIndexDatapoint[];
  authClient: GoogleAuth;
  projectId: string;
  location: string;
  indexId: string;
}

export async function upsertDatapoints(params: UpsertDatapointsParams) {
  const { datapoints, authClient, projectId, location, indexId } = params;
  const accessToken = await authClient.getAccessToken();
  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/indexes/${indexId}:upsertDatapoints`;

  const requestBody = {
    datapoints: datapoints.map((dp) => ({
      datapoint_id: dp.datapointId,
      feature_vector: dp.featureVector,
    })),
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
    logger.error(response);
    throw new Error(`Error: ${JSON.stringify(response.body, null, 2)}`);
  }
}
