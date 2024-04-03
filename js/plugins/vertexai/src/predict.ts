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
import { PluginOptions } from '.';

function endpoint(options: {
  projectId: string;
  location: string;
  model: string;
}) {
  // eslint-disable-next-line max-len
  return `https://${options.location}-aiplatform.googleapis.com/v1/projects/${options.projectId}/locations/${options.location}/publishers/google/models/${options.model}:predict`;
}

interface PredictionResponse<R> {
  predictions: R[];
}

export function predictModel<I = unknown, R = unknown, P = unknown>(
  auth: GoogleAuth,
  { location, projectId }: PluginOptions,
  model: string
) {
  return async (
    instances: I[],
    parameters?: P
  ): Promise<PredictionResponse<R>> => {
    const fetch = (await import('node-fetch')).default;
    // TODO: Don't do it this way.
    const accessToken = await (
      await auth.getApplicationDefault()
    ).credential.getAccessToken();

    const req = {
      instances,
      parameters: parameters || {},
    };

    const response = await fetch(
      endpoint({
        projectId: projectId!,
        location,
        model,
      }),
      {
        method: 'POST',
        body: JSON.stringify(req),
        headers: {
          Authorization: `Bearer ${accessToken.token}`,
          'Content-Type': 'application/json',
          'User-Agent': 'genkit',
        },
      }
    );

    if (!response.ok) {
      throw new Error(
        `Error from Vertex AI predict: HTTP ${
          response.status
        }: ${await response.text()}`
      );
    }

    return (await response.json()) as PredictionResponse<R>;
  };
}
