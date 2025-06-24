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

import { GENKIT_CLIENT_HEADER } from 'genkit';

export type PredictMethod = 'predict' | 'predictLongRunning';

export interface Operation {
  name: string;
  done?: boolean;
  error?: {
    message: string;
  };
  response?: {
    generateVideoResponse: {
      generatedSamples: { video: { uri: string } }[];
    };
  };
}

function predictEndpoint(options: {
  apiVersion: string;
  model: string;
  apiKey: string;
  method: PredictMethod;
}) {
  return `https://generativelanguage.googleapis.com/${options.apiVersion}/models/${options.model}:${options.method}?key=${options.apiKey}`;
}

function opCheckEndpoint(options: {
  apiVersion: string;
  operation: string;
  apiKey: string;
}) {
  return `https://generativelanguage.googleapis.com/${options.apiVersion}/${options.operation}?key=${options.apiKey}`;
}

export type PredictClient<I = unknown, R = unknown, P = unknown> = (
  instances: I[],
  parameters: P
) => Promise<R>;

export function predictModel<I = unknown, R = unknown, P = unknown>(
  model: string,
  apiKey: string,
  method: PredictMethod
): PredictClient<I, R, P> {
  return async (instances: I[], parameters: P): Promise<R> => {
    const fetch = (await import('node-fetch')).default;

    const req = {
      instances,
      parameters,
    };

    const response = await fetch(
      predictEndpoint({
        model,
        apiVersion: 'v1beta',
        apiKey,
        method,
      }),
      {
        method: 'POST',
        body: JSON.stringify(req),
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
      }
    );

    if (!response.ok) {
      throw new Error(
        `Error from Gemini AI predict: HTTP ${
          response.status
        }: ${await response.text()}`
      );
    }

    return (await response.json()) as R;
  };
}

export async function checkOp(
  operation: string,
  apiKey: string
): Promise<Operation> {
  const fetch = (await import('node-fetch')).default;

  const response = await fetch(
    opCheckEndpoint({
      apiVersion: 'v1beta',
      operation,
      apiKey,
    }),
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `Error from operation API: HTTP ${
        response.status
      }: ${await response.text()}`
    );
  }

  return (await response.json()) as Operation;
}
