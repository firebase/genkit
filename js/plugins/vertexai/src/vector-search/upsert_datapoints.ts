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

import { GoogleAuth } from 'google-auth-library';
import { IIndexDatapoint } from './types';

interface UpsertDatapointsParams {
  datapoints: IIndexDatapoint[];
  authClient: GoogleAuth;
  projectId: string;
  location: string;
  indexId: string;
}

/**
 * Upserts datapoints into a specified index.
 *
 * This function sends a request to the Google AI Platform to upsert datapoints
 * into a specified index using the provided parameters.
 *
 * @param {UpsertDatapointsParams} params - The parameters required to upsert datapoints.
 * @param {IIndexDatapoint[]} params.datapoints - The datapoints to be upserted.
 * @param {GoogleAuth} params.authClient - The GoogleAuth client for authorization.
 * @param {string} params.projectId - The ID of the Google Cloud project.
 * @param {string} params.location - The location of the AI Platform index.
 * @param {string} params.indexId - The ID of the index.
 * @returns {Promise<void>} - A promise that resolves when the upsert is complete.
 * @throws {Error} - Throws an error if the upsert fails.
 */
export async function upsertDatapoints(
  params: UpsertDatapointsParams
): Promise<void> {
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
    throw new Error(
      `Error upserting datapoints into index ${indexId}: ${response.statusText}`
    );
  }
}
