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

import { GENKIT_CLIENT_HEADER } from 'genkit';
import { enhanceContentResponse } from '../common/utils';
import {
  EmbedContentRequest,
  EmbedContentResponse,
  EnhancedGenerateContentResponse,
  GenerateContentCandidate,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerateContentStreamResult,
  ListModelsResponse,
  Model,
  Part,
  RequestOptions,
} from './types';

/**
 * Lists available models.
 *
 * https://ai.google.dev/api/models#method:-models.list
 *
 * @param apiKey The API key to authenticate the request.
 * @param requestOptions Optional options to customize the request
 * @returns A promise that resolves to an array of Model objects.
 */
export async function listModels(
  apiKey: string,
  requestOptions?: RequestOptions
): Promise<Model[]> {
  const url = getGoogleAIUrl({
    resourcePath: 'models',
    queryParams: 'pageSize=1000',
    requestOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'GET',
    headers: getHeaders(apiKey, requestOptions),
  };
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
 * @param {RequestOptions} [requestOptions] Optional request options.
 * @returns {Promise<EnhancedGenerateContentResponse>} A promise that resolves to the enhanced content generation response.
 * @throws {Error} If the API request fails or the response cannot be parsed.
 */
export async function generateContent(
  apiKey: string,
  model: string,
  generateContentRequest: GenerateContentRequest,
  requestOptions?: RequestOptions
): Promise<EnhancedGenerateContentResponse> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'generateContent',
    requestOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: getHeaders(apiKey, requestOptions),
    body: JSON.stringify(generateContentRequest),
  };
  const response = await makeRequest(url, fetchOptions);

  const responseJSon = (await response.json()) as GenerateContentResponse;
  return await enhanceContentResponse(responseJSon);
}

/**
 * Generates a stream of content using the Google AI API.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {string} model The name of the model to use for content generation.
 * @param {GenerateContentRequest} generateContentRequest The request object containing the content generation parameters.
 * @param {RequestOptions} [requestOptions] Optional request options.
 * @returns {Promise<GenerateContentStreamResult>} A promise that resolves to an object containing a both the stream and aggregated response.
 * @throws {Error} If the API request fails.
 */
export async function generateContentStream(
  apiKey: string,
  model: string,
  generateContentRequest: GenerateContentRequest,
  requestOptions?: RequestOptions
): Promise<GenerateContentStreamResult> {
  const url = getGoogleAIUrl({
    resourcePath: `models/${model}`,
    resourceMethod: 'streamGenerateContent',
    requestOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: getHeaders(apiKey, requestOptions),
    body: JSON.stringify(generateContentRequest),
  };

  const response = await makeRequest(url, fetchOptions);
  return processStream(response);
}

/**
 * Embeds content using the Google AI API.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {string} model The name of the model to use for content embedding.
 * @param {EmbedContentRequest} embedContentRequest The request object containing the content to embed.
 * @param {RequestOptions} [requestOptions] Optional request options.
 * @returns {Promise<EmbedContentResponse>} A promise that resolves to the embedding response.
 * @throws {Error} If the API request fails or the response cannot be parsed.
 */
export async function embedContent(
  apiKey: string,
  model: string,
  embedContentRequest: EmbedContentRequest,
  requestOptions?: RequestOptions
): Promise<EmbedContentResponse> {
  const url = getGoogleAIUrl({
    resourcePath: `embedders/${model}`,
    resourceMethod: 'embedContent',
    requestOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: getHeaders(apiKey, requestOptions),
    body: JSON.stringify(embedContentRequest),
  };

  const response = await makeRequest(url, fetchOptions);
  return response.json();
}

/**
 * Generates a Google AI URL.
 *
 * @param params - An object containing the parameters for the URL.
 * @param params.path - The path for the URL (the part after the version)
 * @param params.task - An optional task
 * @param params.queryParams - An optional string of '&' delimited query parameters.
 * @param params.requestOptions - An optional object containing request options.
 * @returns The generated Google AI URL.
 */
export function getGoogleAIUrl(params: {
  resourcePath: string;
  resourceMethod?: string;
  queryParams?: string;
  requestOptions?: RequestOptions;
}): string {
  // v1beta is the default because all the new experimental models
  // are found here but not in v1.
  const DEFAULT_API_VERSION = 'v1beta';
  const DEFAULT_BASE_URL = ' https://generativelanguage.googleapis.com';

  const apiVersion = params.requestOptions?.apiVersion || DEFAULT_API_VERSION;
  const baseUrl = params.requestOptions?.baseUrl || DEFAULT_BASE_URL;

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

/**
 * Constructs the headers for an API request.
 *
 * @param {string} apiKey The API key for authentication.
 * @param {RequestOptions} [requestOptions] Optional request options, containing custom headers.
 * @returns {HeadersInit} An object containing the headers to be included in the request.
 */
function getHeaders(
  apiKey: string,
  requestOptions?: RequestOptions
): HeadersInit {
  let customHeaders = {};
  if (requestOptions?.customHeaders) {
    customHeaders = structuredClone(requestOptions.customHeaders);
    delete customHeaders['x-goog-api-key']; // Not allowed in user settings
    delete customHeaders['x-goog-api-client']; // Not allowed in user settings
  }
  const headers: HeadersInit = {
    ...customHeaders,
    'Content-Type': 'application/json',
    'x-goog-api-key': apiKey,
    'x-goog-api-client': GENKIT_CLIENT_HEADER,
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
      const json = await response.json();
      throw new Error(
        `Error fetching from ${url}: [${response.status} ${response.statusText}] ${json.error.message}`
      );
    }
    return response;
  } catch (e) {
    console.error(e);
    throw new Error(`Failed to fetch from ${url}: ${JSON.stringify(e)}`);
  }
}

/**
 * Aggregates multiple `GenerateContentResponse` objects into a single response.
 *
 * This function takes an array of `GenerateContentResponse` objects, from
 * a stream of responses from a generative model, and combines
 * them into a single `GenerateContentResponse`. It handles multiple candidates
 * and parts within those candidates, merging them as they arrive.
 *
 * The function prioritizes the most recent information for candidate metadata
 * (e.g., `citationMetadata`, `groundingMetadata`, `finishReason`, `finishMessage`, `safetyRatings`)
 * while concatenating the content parts.
 *
 * @param responses An array of `GenerateContentResponse` objects to aggregate.
 * @returns A single `GenerateContentResponse` object containing the aggregated data.
 */
function aggregateResponses(
  responses: GenerateContentResponse[]
): GenerateContentResponse {
  const lastResponse = responses[responses.length - 1];
  const aggregatedResponse: GenerateContentResponse = {
    promptFeedback: lastResponse?.promptFeedback,
  };
  for (const response of responses) {
    if (response.candidates) {
      let candidateIndex = 0;
      for (const candidate of response.candidates) {
        if (!aggregatedResponse.candidates) {
          aggregatedResponse.candidates = [];
        }
        if (!aggregatedResponse.candidates[candidateIndex]) {
          aggregatedResponse.candidates[candidateIndex] = {
            index: candidateIndex,
          } as GenerateContentCandidate;
        }
        // Keep overwriting, the last one will be final
        aggregatedResponse.candidates[candidateIndex].citationMetadata =
          candidate.citationMetadata;
        aggregatedResponse.candidates[candidateIndex].groundingMetadata =
          candidate.groundingMetadata;
        aggregatedResponse.candidates[candidateIndex].finishReason =
          candidate.finishReason;
        aggregatedResponse.candidates[candidateIndex].finishMessage =
          candidate.finishMessage;
        aggregatedResponse.candidates[candidateIndex].safetyRatings =
          candidate.safetyRatings;

        /**
         * Candidates should always have content and parts, but this handles
         * possible malformed responses.
         */
        if (candidate.content && candidate.content.parts) {
          if (!aggregatedResponse.candidates[candidateIndex].content) {
            aggregatedResponse.candidates[candidateIndex].content = {
              role: candidate.content.role || 'user',
              parts: [],
            };
          }
          const newPart: Partial<Part> = {};
          for (const part of candidate.content.parts) {
            if (part.text) {
              newPart.text = part.text;
            }
            if (part.functionCall) {
              newPart.functionCall = part.functionCall;
            }
            if (part.executableCode) {
              newPart.executableCode = part.executableCode;
            }
            if (part.codeExecutionResult) {
              newPart.codeExecutionResult = part.codeExecutionResult;
            }
            if (Object.keys(newPart).length === 0) {
              newPart.text = '';
            }
            aggregatedResponse.candidates[candidateIndex].content.parts.push(
              newPart as Part
            );
          }
        }
      }
      candidateIndex++;
    }
    if (response.usageMetadata) {
      aggregatedResponse.usageMetadata = response.usageMetadata;
    }
  }
  return aggregatedResponse;
}

/**
 * Processes an HTTP `Response` object containing a stream of data.
 *
 * @param response The HTTP `Response` object containing the stream. It is expected
 *                 that the response body is not null.
 * @returns A `GenerateContentStreamResult` object containing the `stream` and `response`
 *          properties.
 */
function processStream(response: Response): GenerateContentStreamResult {
  const inputStream = response.body!.pipeThrough(
    new TextDecoderStream('utf8', { fatal: true })
  );
  const responseStream =
    getResponseStream<GenerateContentResponse>(inputStream);
  const [stream1, stream2] = responseStream.tee();
  return {
    stream: generateResponseSequence(stream1),
    response: getResponsePromise(stream2),
  };
}

/**
 * Transforms a stream of strings into a stream of parsed JSON objects.
 *
 * @param inputStream The ReadableStream emitting strings to be processed.
 * @returns A new ReadableStream emitting objects of type T.
 * @throws {Error} If there's an error reading from the stream, parsing JSON, or if the stream ends with unparsed text.
 */
function getResponseStream<T>(
  inputStream: ReadableStream<string>
): ReadableStream<T> {
  const responseLineRE = /^data: (.*)(?:\n\n|\r\r|\r\n\r\n)/;
  const reader = inputStream.getReader();
  const stream = new ReadableStream<T>({
    start(controller) {
      let currentText = '';
      return pump();
      function pump(): Promise<(() => Promise<void>) | undefined> {
        return reader
          .read()
          .then(({ value, done }) => {
            if (done) {
              if (currentText.trim()) {
                controller.error(new Error('Failed to parse stream'));
                return;
              }
              controller.close();
              return;
            }

            currentText += value;
            let match = currentText.match(responseLineRE);
            let parsedResponse: T;
            while (match) {
              try {
                parsedResponse = JSON.parse(match[1]);
              } catch (e) {
                controller.error(
                  new Error(`Error parsing JSON response: "${match[1]}"`)
                );
                return;
              }
              controller.enqueue(parsedResponse);
              currentText = currentText.substring(match[0].length);
              match = currentText.match(responseLineRE);
            }
            return pump();
          })
          .catch((e: Error) => {
            let err = e;
            err.stack = e.stack;
            if (err.name === 'AbortError') {
              err = new Error('Request aborted when reading from the stream');
            } else {
              err = new Error('Error reading from the stream');
            }
            throw err;
          });
      }
    },
  });
  return stream;
}

/**
 * Asynchronously generates a sequence of `EnhancedGenerateContentResponse` objects
 * from a ReadableStream of `GenerateContentResponse` objects.
 *
 * @param stream The ReadableStream emitting `GenerateContentResponse` objects.
 * @returns An AsyncGenerator that yields `EnhancedGenerateContentResponse` objects.
 */
async function* generateResponseSequence(
  stream: ReadableStream<GenerateContentResponse>
): AsyncGenerator<EnhancedGenerateContentResponse> {
  const reader = stream.getReader();
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    yield enhanceContentResponse(value);
  }
}

/**
 * Asynchronously processes a ReadableStream of `GenerateContentResponse` objects
 * and returns a single `EnhancedGenerateContentResponse` Promise.
 *
 * @param stream The ReadableStream emitting `GenerateContentResponse` objects.
 * @returns A Promise that resolves to an `EnhancedGenerateContentResponse` object.
 */
async function getResponsePromise(
  stream: ReadableStream<GenerateContentResponse>
): Promise<EnhancedGenerateContentResponse> {
  const allResponses: GenerateContentResponse[] = [];
  const reader = stream.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      return enhanceContentResponse(aggregateResponses(allResponses));
    }
    allResponses.push(value);
  }
}