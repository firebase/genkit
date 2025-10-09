/**
 * Copyright 2025 Google LLC
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

import {
  extractErrMsg,
  getGenkitClientHeader,
  processStream,
} from '../common/utils.js';
import {
  ClientOptions,
  EmbedContentRequest,
  EmbedContentResponse,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerateContentStreamResult,
  ImagenPredictRequest,
  ImagenPredictResponse,
  ListModelsResponse,
  Model,
  VeoOperation,
  VeoPredictRequest,
} from './types.js';

/**
 * Lists available models.
 *
 * https://ai.google.dev/api/models#method:-models.list
 *
 * @param apiKey The API key to authenticate the request.
 * @param clientOptions Optional options to customize the request
 * @returns A promise that resolves to an array of Model objects.
 */
export async function listModels(
  apiKey: string,
  clientOptions?: ClientOptions
): Promise<Model[]> {
  const url = getGoogleAIUrl({
    resourcePath: 'models',
    queryParams: 'pageSize=1000',
    clientOptions,
  });
  const fetchOptions = getFetchOptions({
    method: 'GET',
    apiKey,
    clientOptions,
  });
  const response = await makeRequest(url, fetchOptions);
  const modelResponse = JSON.parse(await response.text()) as ListModelsResponse;
  return modelResponse.models;
}

/**
 * Generates content using the Google AI API.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {string} model The name of the model to use for content generation.
 * @param {GenerateContentRequest} generateContentRequest The request object containing the content generation parameters.
 * @param {ClientOptions} [clientOptions] Optional client options.
 * @returns {Promise<GenerateContentResponse>} A promise that resolves to the content generation response.
 * @throws {Error} If the API request fails or the response cannot be parsed.
 */
export async function generateContent(
  apiKey: string,
  model: string,
  generateContentRequest: GenerateContentRequest,
  clientOptions?: ClientOptions
): Promise<GenerateContentResponse> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'generateContent',
    clientOptions,
  });
  const fetchOptions = getFetchOptions({
    method: 'POST',
    apiKey,
    clientOptions,
    body: JSON.stringify(generateContentRequest),
  });
  const response = await makeRequest(url, fetchOptions);

  const responseJson = (await response.json()) as GenerateContentResponse;
  return responseJson;
}

/**
 * Generates a stream of content using the Google AI API.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {string} model The name of the model to use for content generation.
 * @param {GenerateContentRequest} generateContentRequest The request object containing the content generation parameters.
 * @param {ClientOptions} [clientOptions] Optional client options.
 * @returns {Promise<GenerateContentStreamResult>} A promise that resolves to an object containing a both the stream and aggregated response.
 * @throws {Error} If the API request fails.
 */
export async function generateContentStream(
  apiKey: string,
  model: string,
  generateContentRequest: GenerateContentRequest,
  clientOptions?: ClientOptions
): Promise<GenerateContentStreamResult> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'streamGenerateContent',
    clientOptions,
  });
  const fetchOptions = getFetchOptions({
    method: 'POST',
    apiKey,
    clientOptions,
    body: JSON.stringify(generateContentRequest),
  });

  const response = await makeRequest(url, fetchOptions);
  return processStream(response);
}

/**
 * Embeds content using the Google AI API.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {string} model The name of the model to use for content embedding.
 * @param {EmbedContentRequest} embedContentRequest The request object containing the content to embed.
 * @param {ClientOptions} [clientOptions] Optional client options.
 * @returns {Promise<EmbedContentResponse>} A promise that resolves to the embedding response.
 * @throws {Error} If the API request fails or the response cannot be parsed.
 */
export async function embedContent(
  apiKey: string,
  model: string,
  embedContentRequest: EmbedContentRequest,
  clientOptions?: ClientOptions
): Promise<EmbedContentResponse> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'embedContent',
    clientOptions,
  });
  const fetchOptions = getFetchOptions({
    method: 'POST',
    apiKey,
    clientOptions,
    body: JSON.stringify(embedContentRequest),
  });

  const response = await makeRequest(url, fetchOptions);
  return response.json();
}

export async function imagenPredict(
  apiKey: string,
  model: string,
  imagenPredictRequest: ImagenPredictRequest,
  clientOptions?: ClientOptions
): Promise<ImagenPredictResponse> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'predict',
    clientOptions,
  });

  const fetchOptions = getFetchOptions({
    method: 'POST',
    apiKey,
    clientOptions,
    body: JSON.stringify(imagenPredictRequest),
  });

  const response = await makeRequest(url, fetchOptions);
  return response.json() as Promise<ImagenPredictResponse>;
}

export async function veoPredict(
  apiKey: string,
  model: string,
  veoPredictRequest: VeoPredictRequest,
  clientOptions?: ClientOptions
): Promise<VeoOperation> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'predictLongRunning',
    clientOptions,
  });

  const fetchOptions = getFetchOptions({
    method: 'POST',
    apiKey,
    clientOptions,
    body: JSON.stringify(veoPredictRequest),
  });

  const response = await makeRequest(url, fetchOptions);
  return response.json() as Promise<VeoOperation>;
}

export async function veoCheckOperation(
  apiKey: string,
  operation: string,
  clientOptions?: ClientOptions
): Promise<VeoOperation> {
  const url = getGoogleAIUrl({
    resourcePath: operation,
    clientOptions,
  });
  const fetchOptions = getFetchOptions({
    method: 'GET',
    apiKey,
    clientOptions,
  });

  const response = await makeRequest(url, fetchOptions);
  return response.json() as Promise<VeoOperation>;
}

/**
 * Generates a Google AI URL.
 *
 * @param params - An object containing the parameters for the URL.
 * @param params.path - The path for the URL (the part after the version)
 * @param params.task - An optional task
 * @param params.queryParams - An optional string of '&' delimited query parameters.
 * @param params.clientOptions - An optional object containing client options.
 * @returns The generated Google AI URL.
 */
export function getGoogleAIUrl(params: {
  resourcePath: string;
  resourceMethod?: string;
  queryParams?: string;
  clientOptions?: ClientOptions;
}): string {
  // v1beta is the default because all the new experimental models
  // are found here but not in v1.
  const DEFAULT_API_VERSION = 'v1beta';
  const DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com';

  const apiVersion = params.clientOptions?.apiVersion || DEFAULT_API_VERSION;
  const baseUrl = params.clientOptions?.baseUrl || DEFAULT_BASE_URL;

  let url = `${baseUrl}/${apiVersion}/${params.resourcePath}`;
  if (params.resourceMethod) {
    url += `:${params.resourceMethod}`;
  }
  if (params.queryParams) {
    url += `?${params.queryParams}`;
  }
  if (params.resourceMethod === 'streamGenerateContent') {
    url += `${params.queryParams ? '&' : '?'}alt=sse`;
  }
  return url;
}

function getFetchOptions(params: {
  method: 'POST' | 'GET';
  apiKey: string;
  body?: string;
  clientOptions?: ClientOptions;
}) {
  const fetchOptions: RequestInit = {
    method: params.method,
    headers: getHeaders(params.apiKey, params.clientOptions),
  };
  if (params.body) {
    fetchOptions.body = params.body;
  }
  const signal = getAbortSignal(params.clientOptions);
  if (signal) {
    fetchOptions.signal = signal;
  }
  return fetchOptions;
}

function getAbortSignal(
  clientOptions?: ClientOptions
): AbortSignal | undefined {
  const hasTimeout = (clientOptions?.timeout ?? -1) >= 0;
  if (clientOptions?.signal !== undefined || hasTimeout) {
    const controller = new AbortController();
    if (hasTimeout) {
      setTimeout(() => controller.abort(), clientOptions?.timeout);
    }
    if (clientOptions?.signal) {
      clientOptions.signal.addEventListener('abort', () => {
        controller.abort();
      });
    }
    return controller.signal;
  }
  return undefined;
}

/**
 * Constructs the headers for an API request.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {ClientOptions} [clientOptions] Optional client options, containing custom headers.
 * @returns {HeadersInit} An object containing the headers to be included in the request.
 */
function getHeaders(
  apiKey: string,
  clientOptions?: ClientOptions
): HeadersInit {
  let customHeaders = {};
  if (clientOptions?.customHeaders) {
    customHeaders = structuredClone(clientOptions.customHeaders);
    delete customHeaders['x-goog-api-key']; // Not allowed in user settings
    delete customHeaders['x-goog-api-client']; // Not allowed in user settings
  }
  const headers: HeadersInit = {
    ...customHeaders,
    'Content-Type': 'application/json',
    'x-goog-api-key': apiKey,
    'x-goog-api-client': getGenkitClientHeader(),
  };

  return headers;
}

/**
 * Makes a request to the specified URL with the provided options.
 *
 * @param {string} url The URL to make the request to.
 * @param {RequestInit} fetchOptions The options to pass to the `fetch` API.
 * @returns {Promise<Response>} A promise that resolves to the Response
 * @throws {Error} If the request fails
 */
async function makeRequest(
  url: string,
  fetchOptions: RequestInit
): Promise<Response> {
  try {
    const response = await fetch(url, fetchOptions);
    if (!response.ok) {
      let errorText = await response.text();
      let errorMessage = errorText;
      try {
        const json = JSON.parse(errorText);
        if (json.error && json.error.message) {
          errorMessage = json.error.message;
        }
      } catch (e) {
        // Not JSON or expected format, use the raw text
      }
      throw new Error(
        `Error fetching from ${url}: [${response.status} ${response.statusText}] ${errorMessage}`
      );
    }
    return response;
  } catch (e: unknown) {
    console.error(e);
    throw new Error(`Failed to fetch from ${url}: ${extractErrMsg(e)}`);
  }
}

export const TEST_ONLY = {
  getFetchOptions,
  getAbortSignal,
  getHeaders,
  makeRequest,
};
