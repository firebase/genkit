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

// Gemini  model definition
export interface Model {
  name: string;
  baseModelId: string;
  version: string;
  displayName: string;
  description: string;
  inputTokenLimit: number;
  outputTokenLimit: number;
  supportedGenerationMethods: string[];
  temperature: number;
  maxTemperature: number;
  topP: number;
  topK: number;
}

// Gemini list models response
interface ListModelsResponse {
  models: Model[];
  nextPageToken?: string;
}

/**
 * List Gemini models by making an RPC call to the API.
 *
 * https://ai.google.dev/api/models#method:-models.list
 */
export async function listModels(
  baseUrl: string,
  apiKey: string
): Promise<Model[]> {
  // We call the gemini list local models api:
  const res = await fetch(
    `${baseUrl}/v1beta/models?pageSize=1000&key=${apiKey}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
  const modelResponse = JSON.parse(await res.text()) as ListModelsResponse;
  return modelResponse.models;
}
