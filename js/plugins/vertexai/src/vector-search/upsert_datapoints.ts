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
